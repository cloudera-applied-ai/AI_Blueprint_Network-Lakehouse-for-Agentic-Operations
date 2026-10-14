"""Background tasks for continuous data generation"""
import asyncio
import math
import random
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.exc import OperationalError, IntegrityError, DBAPIError

from sqlalchemy.dialects.postgresql import insert as pg_insert

from .database import SessionLocal
from .models import FiberNodeModel, KPIMetricsModel, AlertModel, SelfHealingActionModel
from .generator import generate_node_kpi_metrics, generate_cable_alert, generate_auto_resolution_action
from .slack_service import slack_service
from .weather_service import weather_service, WeatherConditions

from .config import settings

# Configuration for historical data generation (overridable via env / .env, see config.py).
# Kept within the raw retention window so the backfill is not immediately deleted.
HISTORICAL_HOURS = min(settings.HISTORICAL_BACKFILL_HOURS, settings.RETENTION_RAW_HOURS)
HISTORICAL_INTERVAL_MINUTES = settings.HISTORICAL_INTERVAL_MINUTES

# Max retries for handling write-write conflicts
MAX_RETRIES = 3
RETRY_DELAY = 0.5  # seconds


class BackgroundDataGenerator:
    """Background service that continuously generates KPIs, alerts, and actions"""

    def __init__(self):
        self.running = False
        self.paused = False  # When True, skips data generation cycles
        self.data_ready = False  # True when historical data is loaded and we have node data
        self.task: Optional[asyncio.Task] = None
        self.insights_task: Optional[asyncio.Task] = None  # AI insights generation task
        self.weather_task: Optional[asyncio.Task] = None   # Weather fetch task
        self.kpi_interval = settings.KPI_GENERATION_INTERVAL_SECONDS  # Seconds between KPI rows for a given node
        self.cycle_seconds = settings.KPI_CYCLE_SECONDS  # Loop tick; each tick covers a rotating slice of nodes
        self._cycle_offset = 0  # Round-robin position into the node list
        self.insights_interval = 30  # Generate AI insights every 30 seconds
        self.weather_interval = 300  # Fetch weather every 5 minutes (300 seconds)
        self.alert_probability = 0.008  # 0.8% chance per node per cycle (increased for demo - shows auto-repair)
        # Track running analysis tasks to prevent unbounded accumulation
        self._pending_analysis_tasks: set = set()
        self._max_concurrent_analyses = 5  # Limit concurrent AI analyses

        # === WEATHER DATA ===
        # Cache of node locations for weather lookup: node_id -> (lat, lng)
        self._node_locations: Dict[str, tuple] = {}
        # Cache of weather data per node: node_id -> weather_dict
        self._node_weather: Dict[str, Dict] = {}
        self._last_weather_fetch: Optional[datetime] = None

        # === NODE ID CACHE ===
        self._cached_node_ids: list = []
        self._node_ids_last_refreshed: Optional[datetime] = None
        self._node_ids_refresh_interval = 60  # Refresh node ID list every 60 seconds

        # === AI OPTIMIZATION SETTINGS ===
        # LLM sampling: only use LLM for 1 in N alerts, rest use rule-based
        self.llm_sample_rate = 5  # 1 in 5 alerts use LLM (20%), rest use fast rule-based
        self._alert_counter = 0  # Track alerts for sampling

        # Node cooldown: don't re-analyze same node within cooldown period
        self.node_cooldown_minutes = 15  # Minutes before re-analyzing same node
        self._node_last_analyzed: dict = {}  # node_id -> datetime

        # Analysis cache: cache results for similar alert patterns
        self._analysis_cache: dict = {}  # cache_key -> (analysis, timestamp)
        self._cache_ttl_minutes = 30  # Cache entries expire after 30 minutes

        self.stats = {
            "kpis_generated": 0,
            "alerts_generated": 0,
            "actions_generated": 0,
            "insights_generated": 0,
            "last_insights_run": None,
            "last_run": None,
            "cycles": 0,
            "skipped_cycles": 0,  # Track cycles skipped due to pause
            # AI optimization stats
            "ai_analyses_llm": 0,  # Alerts analyzed with LLM
            "ai_analyses_rule_based": 0,  # Alerts analyzed with rules
            "ai_analyses_cached": 0,  # Alerts using cached analysis
            "ai_analyses_cooled_down": 0,  # Alerts skipped due to node cooldown
            # Weather stats
            "weather_fetches": 0,
            "weather_api_calls": 0,
            "weather_errors": 0,
            "last_weather_fetch": None,
        }

    def pause(self):
        """Pause data generation (keeps loop running but skips generation)"""
        self.paused = True
        print("⏸️ Data generation PAUSED")

    def resume(self):
        """Resume data generation"""
        self.paused = False
        print("▶️ Data generation RESUMED")

    def is_paused(self) -> bool:
        """Check if data generation is paused"""
        return self.paused

    def get_db(self) -> Session:
        """Get database session"""
        return SessionLocal()

    def _sync_node_statuses_with_alerts(self):
        """Sync node statuses with existing active alerts at startup.

        This ensures nodes show correct status (outage/degraded) based on
        any active alerts that exist in the database.
        """
        db = self.get_db()
        try:
            from sqlalchemy import update as sql_update

            # Get all nodes with active CRITICAL alerts -> set to outage
            # Note: severity is stored uppercase in database
            critical_nodes_query = select(AlertModel.node_id).where(
                AlertModel.status == 'ACTIVE',
                AlertModel.severity.in_(['CRITICAL', 'critical'])
            ).distinct()
            critical_result = db.execute(critical_nodes_query).fetchall()
            critical_node_ids = [row[0] for row in critical_result]

            if critical_node_ids:
                update_stmt = sql_update(FiberNodeModel).where(
                    FiberNodeModel.node_id.in_(critical_node_ids)
                ).values(status='outage')
                db.execute(update_stmt)
                print(f"🔄 Synced {len(critical_node_ids)} nodes to 'outage' status (active CRITICAL alerts)")

            # Get all nodes with active WARNING alerts (but not CRITICAL) -> set to degraded
            # Note: severity is stored uppercase in database
            warning_nodes_query = select(AlertModel.node_id).where(
                AlertModel.status == 'ACTIVE',
                AlertModel.severity.in_(['WARNING', 'warning'])
            ).distinct()
            warning_result = db.execute(warning_nodes_query).fetchall()
            warning_node_ids = [row[0] for row in warning_result]

            # Exclude nodes that already have critical alerts (they should stay outage)
            warning_only_ids = [nid for nid in warning_node_ids if nid not in critical_node_ids]

            if warning_only_ids:
                update_stmt = sql_update(FiberNodeModel).where(
                    FiberNodeModel.node_id.in_(warning_only_ids)
                ).values(status='degraded')
                db.execute(update_stmt)
                print(f"🔄 Synced {len(warning_only_ids)} nodes to 'degraded' status (active WARNING alerts)")

            db.commit()
            print("✅ Node status sync complete")

        except Exception as e:
            db.rollback()
            print(f"⚠️ Error syncing node statuses: {e}")
        finally:
            db.close()

    def _seed_network_devices(self):
        """Seed network devices if table is empty (same pattern as headend/hub seeding)."""
        db = self.get_db()
        try:
            from .seed_network_devices import seed_network_devices
            count = seed_network_devices(db)
            if count > 0:
                print(f"🔧 Seeded {count} network devices (firewalls, switches, routers)")
        except Exception as e:
            db.rollback()
            print(f"⚠️ Error seeding network devices: {e}")
        finally:
            db.close()

    def _seed_customers(self):
        """Seed customer accounts and sentiment if table is empty."""
        db = self.get_db()
        try:
            from .seed_customers import seed_customers
            count = seed_customers(db)
            if count > 0:
                print(f"👥 Seeded {count} customer accounts with sentiment data")
        except Exception as e:
            db.rollback()
            print(f"⚠️ Error seeding customers: {e}")
        finally:
            db.close()

    async def start(self):
        """Start background data generation"""
        if self.running:
            print("⚠️ Background generator already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._run_loop())
        self.insights_task = asyncio.create_task(self._generate_insights_loop())
        self.weather_task = asyncio.create_task(self._weather_fetch_loop())
        print("🚀 Background data generator started")
        print("🧠 AI insights generator started (runs every 30s)")
        print("🌤️ Weather service started (fetches every 5 min)")

        # Sync node statuses with existing alerts at startup
        self._sync_node_statuses_with_alerts()

        # Seed network devices if table is empty
        self._seed_network_devices()

        # Seed customer accounts if table is empty
        self._seed_customers()

        # Generate historical data in background AFTER startup completes (non-blocking)
        asyncio.create_task(self._ensure_historical_data_background())

    async def _ensure_historical_data_background(self):
        """Background wrapper for historical data generation with error handling"""
        try:
            # Small delay to ensure main loop is running first
            await asyncio.sleep(1)
            print("📊 Starting background historical data check...")

            # CRITICAL: Pause the main generator to prevent ID collisions
            was_paused = self.paused
            self.pause()
            print("⏸️ Paused main generator during historical data creation")

            try:
                await self._ensure_historical_data()
            finally:
                # Resume if it wasn't already paused
                if not was_paused:
                    self.resume()
                    print("▶️ Resumed main generator after historical data creation")

        except Exception as e:
            print(f"❌ Background historical data generation failed: {e}")
            import traceback
            traceback.print_exc()

    async def _ensure_historical_data(self):
        """Ensure we have at least some historical KPI data"""
        db = self.get_db()
        try:
            # Check if we have nodes
            node_count_result = db.execute(select(func.count(FiberNodeModel.node_id)))
            node_count = node_count_result.scalar()

            if node_count == 0:
                print("⚠️ No fiber nodes found - skipping historical data generation")
                # Still mark as ready so frontend can connect
                self.data_ready = True
                print("✅ Backend data is ready for connections (no nodes yet)")
                return

            # Check how much KPI data we have
            kpi_count_result = db.execute(select(func.count(KPIMetricsModel.id)))
            kpi_count = kpi_count_result.scalar()

            # Only generate historical data if database is completely empty
            # If ANY data exists, skip generation and use existing data
            if kpi_count == 0:
                print(f"📊 No KPI data found - generating {HISTORICAL_HOURS} hour(s) of historical data...")
                await self._generate_historical_kpis(db, node_count)
            else:
                print(f"✅ Existing data found: {kpi_count:,} KPIs - skipping historical generation")

            # Mark data as ready after historical data check/generation
            self.data_ready = True
            print("✅ Backend data is ready for connections")

        except Exception as e:
            print(f"❌ Error checking historical data: {e}")
            import traceback
            traceback.print_exc()
            # Even on error, mark as ready so frontend doesn't hang forever
            self.data_ready = True
        finally:
            db.close()

    async def _generate_historical_kpis(self, db: Session, node_count: int):
        """Generate historical KPI data for all fiber nodes (memory-efficient streaming approach)"""
        import time
        import gc
        start_time = time.time()

        try:
            # Get all node IDs
            query = select(FiberNodeModel.node_id)
            result = db.execute(query)
            node_ids = [row[0] for row in result.all()]

            if not node_ids:
                print("⚠️ No fiber nodes to generate historical data for")
                return

            # Calculate number of records per node
            records_per_node = max(1, (HISTORICAL_HOURS * 60) // HISTORICAL_INTERVAL_MINUTES)
            total_records_estimate = len(node_ids) * records_per_node

            print(f"   Fiber Nodes: {len(node_ids)}")
            print(f"   Hours: {HISTORICAL_HOURS}, Interval: {HISTORICAL_INTERVAL_MINUTES}m, Records/node: {records_per_node}")
            print(f"   Total records to generate: {total_records_estimate:,}")

            # Generate historical KPIs in SMALL batches to control memory
            total_generated = 0
            batch_size = 1000  # Reduced from 10000 to prevent memory explosion
            now = datetime.now()

            # Process nodes in chunks to allow memory cleanup between chunks
            node_chunk_size = 50  # Process 50 nodes at a time

            for chunk_start in range(0, len(node_ids), node_chunk_size):
                chunk_end = min(chunk_start + node_chunk_size, len(node_ids))
                node_chunk = node_ids[chunk_start:chunk_end]

                current_batch = []

                # Get fresh max ID at start of each chunk to prevent collisions
                max_id_result = db.execute(select(func.max(KPIMetricsModel.id)))
                id_counter = (max_id_result.scalar() or 0) + 1

                for node_id in node_chunk:
                    for i in range(records_per_node):
                        # Go backwards in time from now
                        minutes_ago = i * HISTORICAL_INTERVAL_MINUTES
                        timestamp = now - timedelta(minutes=minutes_ago)

                        kpi_data = generate_node_kpi_metrics(node_id, timestamp)
                        kpi_data['id'] = id_counter
                        id_counter += 1
                        current_batch.append(kpi_data)
                        total_generated += 1

                        # Commit in small batches for memory efficiency
                        if len(current_batch) >= batch_size:
                            insert_stmt = pg_insert(KPIMetricsModel.__table__).values(current_batch)
                            insert_stmt = insert_stmt.on_conflict_do_nothing()
                            db.execute(insert_stmt)
                            db.commit()

                            # Clear batch and force garbage collection
                            current_batch.clear()

                            # Yield to event loop
                            await asyncio.sleep(0)

                # Commit remaining records in this chunk
                if current_batch:
                    insert_stmt = pg_insert(KPIMetricsModel.__table__).values(current_batch)
                    insert_stmt = insert_stmt.on_conflict_do_nothing()
                    db.execute(insert_stmt)
                    db.commit()
                    current_batch.clear()

                # Progress update per chunk
                elapsed = time.time() - start_time
                progress_pct = (total_generated / total_records_estimate) * 100
                records_per_sec = total_generated / elapsed if elapsed > 0 else 0
                print(f"   📊 Processed {chunk_end}/{len(node_ids)} nodes ({progress_pct:.1f}%) | {records_per_sec:.0f} rec/s")

                # Force garbage collection between chunks to free memory
                gc.collect()
                await asyncio.sleep(0.1)  # Small delay to let system breathe

            elapsed = time.time() - start_time
            records_per_sec = total_generated / elapsed if elapsed > 0 else 0
            print(f"✅ Historical KPI generation completed: {total_generated:,} records in {elapsed:.1f}s ({records_per_sec:.0f} rec/s)")

        except Exception as e:
            db.rollback()
            print(f"❌ Error generating historical KPIs: {e}")
            import traceback
            traceback.print_exc()

    async def stop(self):
        """Stop background data generation"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        if self.insights_task:
            self.insights_task.cancel()
            try:
                await self.insights_task
            except asyncio.CancelledError:
                pass
        if self.weather_task:
            self.weather_task.cancel()
            try:
                await self.weather_task
            except asyncio.CancelledError:
                pass
        # Close weather service HTTP client
        await weather_service.close()
        print("🛑 Background data generator stopped")
        print("🛑 AI insights generator stopped")
        print("🛑 Weather service stopped")

    async def _run_loop(self):
        """Main generation loop"""
        while self.running:
            try:
                if self.paused:
                    # Skip generation when paused
                    self.stats["skipped_cycles"] += 1
                else:
                    await self._generate_cycle()
                    self.stats["cycles"] += 1
                    self.stats["last_run"] = datetime.now().isoformat()
            except Exception as e:
                print(f"❌ Background generation error: {e}")

            # Always process existing actions, even when generation is paused
            # or if _generate_cycle failed.  Actions need state transitions
            # (PENDING → IN_PROGRESS → COMPLETED) independent of new data
            # generation.
            try:
                await self._process_actions()
            except Exception as e:
                print(f"❌ Action processing error: {e}")

            await asyncio.sleep(self.cycle_seconds)

    async def _generate_insights_loop(self):
        """Background loop for generating AI insights every 30 seconds"""
        # Wait for initial data to be ready
        while not self.data_ready and self.running:
            await asyncio.sleep(1)

        print("🧠 AI insights generation loop is now active")

        while self.running:
            try:
                if not self.paused:
                    await self._generate_ai_insights()
                    self.stats["last_insights_run"] = datetime.now().isoformat()
            except Exception as e:
                print(f"❌ AI insights generation error: {e}")
                import traceback
                traceback.print_exc()

            await asyncio.sleep(self.insights_interval)

    async def _weather_fetch_loop(self):
        """Background loop for fetching live weather data"""
        # Wait for initial data to be ready
        while not self.data_ready and self.running:
            await asyncio.sleep(1)

        print("🌤️ Weather fetch loop is now active")

        # Initial fetch
        await self._fetch_weather_for_nodes()

        while self.running:
            try:
                await asyncio.sleep(self.weather_interval)
                if not self.paused:
                    await self._fetch_weather_for_nodes()
            except Exception as e:
                print(f"❌ Weather fetch error: {e}")
                self.stats["weather_errors"] += 1

    async def _fetch_weather_for_nodes(self):
        """Fetch weather data for fiber node locations with progressive loading."""
        db = self.get_db()
        try:
            # Load node locations if not cached
            if not self._node_locations:
                query = select(
                    FiberNodeModel.node_id,
                    FiberNodeModel.latitude,
                    FiberNodeModel.longitude
                )
                result = db.execute(query)
                for row in result.all():
                    node_id, lat, lng = row
                    if lat is not None and lng is not None:
                        self._node_locations[node_id] = (lat, lng)
                print(f"🌤️ Loaded {len(self._node_locations)} fiber node locations for weather")

            if not self._node_locations:
                return

            # Get unique location grid cells (weather API caches by ~10km grid)
            # Group nodes by their rounded coordinates
            location_groups: Dict[str, list] = {}
            for node_id, (lat, lng) in self._node_locations.items():
                # Round to 1 decimal (~10km grid) for efficient API usage
                grid_key = f"{round(lat, 1)},{round(lng, 1)}"
                if grid_key not in location_groups:
                    location_groups[grid_key] = []
                location_groups[grid_key].append(node_id)

            # Progressive loading: limit locations per fetch cycle to respect rate limits
            # Weather service enforces 2s min interval, so 30 requests/min max
            # We'll fetch up to 25 unique locations per cycle
            MAX_LOCATIONS_PER_CYCLE = 25

            # Sort by grid_key to ensure consistent ordering
            all_grid_keys = sorted(location_groups.keys())

            # Track which locations still need fetching (not in weather cache)
            locations_to_fetch = []
            for grid_key in all_grid_keys:
                lat, lng = map(float, grid_key.split(","))
                # Check if we already have cached weather from the service
                cached = weather_service.get_cached_weather(lat, lng)
                if cached is None:
                    locations_to_fetch.append(grid_key)

            # Limit how many we fetch this cycle
            locations_this_cycle = locations_to_fetch[:MAX_LOCATIONS_PER_CYCLE]

            if locations_this_cycle:
                print(f"🌤️ Fetching weather for {len(locations_this_cycle)}/{len(all_grid_keys)} locations (progressive)...")
            else:
                # All locations cached, just update node weather from cache
                for grid_key, node_ids in location_groups.items():
                    lat, lng = map(float, grid_key.split(","))
                    cached = weather_service.get_cached_weather(lat, lng)
                    if cached:
                        weather_dict = {
                            "weather_desc": cached.get_weather_description(),
                            "weather_impact": cached.overall_impact,
                            "temperature_outdoor": cached.temperature_c,
                            "precipitation_mm": cached.precipitation_mm,
                            "wind_speed_kmh": cached.wind_speed_kmh,
                            "rain_impact": cached.rain_impact,
                            "temp_impact": cached.temperature_impact,
                            "wind_impact": cached.wind_impact,
                        }
                        for node_id in node_ids:
                            self._node_weather[node_id] = weather_dict

            # Fetch weather for selected locations (rate limiting handled by service)
            fetched_count = 0
            for grid_key in locations_this_cycle:
                lat, lng = map(float, grid_key.split(","))
                node_ids = location_groups[grid_key]

                # Get weather from service (rate limiting handled internally)
                weather = await weather_service.fetch_weather(lat, lng)

                if weather:
                    # Convert to dict format for KPI generation
                    weather_dict = {
                        "weather_desc": weather.get_weather_description(),
                        "weather_impact": weather.overall_impact,
                        "temperature_outdoor": weather.temperature_c,
                        "precipitation_mm": weather.precipitation_mm,
                        "wind_speed_kmh": weather.wind_speed_kmh,
                        "rain_impact": weather.rain_impact,
                        "temp_impact": weather.temperature_impact,
                        "wind_impact": weather.wind_impact,
                    }

                    # Assign to all nodes in this grid cell
                    for node_id in node_ids:
                        self._node_weather[node_id] = weather_dict
                    fetched_count += 1

            self._last_weather_fetch = datetime.now()
            self.stats["weather_fetches"] += 1
            self.stats["last_weather_fetch"] = self._last_weather_fetch.isoformat()

            # Get API stats
            api_stats = weather_service.get_stats()
            self.stats["weather_api_calls"] = api_stats.get("api_calls", 0)
            self.stats["weather_rate_limited"] = api_stats.get("rate_limited", 0)

            # Log summary
            coverage = len(self._node_weather) / len(self._node_locations) * 100 if self._node_locations else 0
            impacted_nodes = sum(1 for w in self._node_weather.values() if w.get("weather_impact", 0) > 0.1)
            print(f"🌤️ Weather: {fetched_count} new, {coverage:.0f}% node coverage, {impacted_nodes} impacted nodes")

        except Exception as e:
            print(f"❌ Error fetching weather: {e}")
            import traceback
            traceback.print_exc()
            self.stats["weather_errors"] += 1
        finally:
            db.close()

    def get_node_weather(self, node_id: str) -> Optional[Dict]:
        """Get cached weather data for a fiber node"""
        return self._node_weather.get(node_id)

    async def _generate_ai_insights(self):
        """Generate AI insights (rule-based, no LLM required)"""
        db = self.get_db()
        try:
            from .ai_insights import generate_rule_based_insights

            # Generate insights
            insights = generate_rule_based_insights(db)

            self.stats["insights_generated"] = len(insights)

            # Log summary every few cycles
            if insights:
                critical_count = len([i for i in insights if i.severity == "critical"])
                warning_count = len([i for i in insights if i.severity == "warning"])
                info_count = len([i for i in insights if i.severity == "info"])
                print(f"🧠 Generated {len(insights)} insights: {critical_count} critical, {warning_count} warning, {info_count} info")

        except Exception as e:
            print(f"❌ Error generating AI insights: {e}")
            import traceback
            traceback.print_exc()
        finally:
            db.close()

    def _get_analysis_cache_key(self, alert_type: str, severity: str, node_region: str) -> str:
        """Generate cache key for analysis results"""
        return f"{alert_type}:{severity}:{node_region}"

    def _is_node_on_cooldown(self, node_id: str) -> bool:
        """Check if node was recently analyzed"""
        last_analyzed = self._node_last_analyzed.get(node_id)
        if not last_analyzed:
            return False
        cooldown_elapsed = (datetime.now() - last_analyzed).total_seconds() / 60
        return cooldown_elapsed < self.node_cooldown_minutes

    def _clean_expired_cache(self):
        """Remove expired cache entries"""
        now = datetime.now()
        expired_keys = [
            key for key, (_, timestamp) in self._analysis_cache.items()
            if (now - timestamp).total_seconds() / 60 > self._cache_ttl_minutes
        ]
        for key in expired_keys:
            del self._analysis_cache[key]

    def _should_use_llm(self) -> bool:
        """Determine if this alert should use LLM (sampling)"""
        self._alert_counter += 1
        return self._alert_counter % self.llm_sample_rate == 0

    async def _analyze_and_execute_alert(self, alert_id: str, node_id: str = None, alert_type: str = None, severity: str = None):
        """
        Analyze a new alert with AI and create/execute action plan.

        This is called automatically when new alerts are generated.
        Includes AI cost optimizations:
        - Node cooldown (skip if recently analyzed)
        - LLM sampling (only use LLM for 1 in N alerts)
        - Analysis caching (reuse similar analyses)
        """
        db = self.get_db()
        try:
            from .ai_analyzer import analyze_new_alert, analyze_alert_rule_based, get_llm_config
            from .autonomous_executor import create_action_plan, execute_plan, save_plan_to_db
            from .models import AlertModel, FiberNodeModel

            # Get alert details if not provided
            if not node_id or not alert_type or not severity:
                alert = db.execute(
                    select(AlertModel).where(AlertModel.alert_id == alert_id)
                ).scalar_one_or_none()
                if alert:
                    node_id = alert.node_id
                    alert_type = alert.type
                    severity = alert.severity

            # OPTIMIZATION 1: Node cooldown check
            if node_id and self._is_node_on_cooldown(node_id):
                self.stats["ai_analyses_cooled_down"] += 1
                print(f"⏳ Skipping analysis for {alert_id[:8]} - node {node_id} on cooldown")
                return

            # Get node region for cache key
            node_region = "unknown"
            if node_id:
                node = db.execute(
                    select(FiberNodeModel).where(FiberNodeModel.node_id == node_id)
                ).scalar_one_or_none()
                if node:
                    node_region = node.region or "unknown"

            # OPTIMIZATION 2: Check analysis cache
            cache_key = self._get_analysis_cache_key(alert_type or "unknown", severity or "warning", node_region)
            self._clean_expired_cache()

            cached = self._analysis_cache.get(cache_key)
            if cached:
                cached_analysis, _ = cached
                # Clone cached analysis with new alert ID
                analysis = cached_analysis
                analysis.alert_id = alert_id
                analysis.node_id = node_id
                self.stats["ai_analyses_cached"] += 1
                print(f"📦 Using cached analysis for {alert_id[:8]} (key: {cache_key[:20]})")
            else:
                # OPTIMIZATION 3: LLM sampling - only use LLM for 1 in N alerts
                llm_config = get_llm_config(db)
                use_llm = llm_config and self._should_use_llm()

                if use_llm:
                    # Use full LLM analysis
                    analysis = await analyze_new_alert(db, alert_id)
                    self.stats["ai_analyses_llm"] += 1
                    print(f"🧠 LLM analysis for {alert_id[:8]}")
                else:
                    # Use fast rule-based analysis
                    analysis = analyze_alert_rule_based(db, alert_id)
                    self.stats["ai_analyses_rule_based"] += 1
                    print(f"📋 Rule-based analysis for {alert_id[:8]}")

                # Cache the result for future similar alerts
                if analysis and cache_key:
                    self._analysis_cache[cache_key] = (analysis, datetime.now())

            if not analysis:
                return

            # Mark node as recently analyzed
            if node_id:
                self._node_last_analyzed[node_id] = datetime.now()

            # Create action plan (rule-based, no additional LLM call needed)
            plan = await create_action_plan(db, analysis, use_llm=False)

            if not plan:
                return

            # Save plan to database
            save_plan_to_db(db, plan)

            # Execute if autonomous execution is recommended
            if analysis.should_execute_autonomously:
                print(f"🤖 Auto-executing plan for alert {alert_id[:8]}")
                await execute_plan(db, plan)
                save_plan_to_db(db, plan)

                self.stats["ai_plans_executed"] = self.stats.get("ai_plans_executed", 0) + 1
            else:
                print(f"⏸️ Plan created for {alert_id[:8]} - manual intervention required")
                self.stats["ai_plans_pending_manual"] = self.stats.get("ai_plans_pending_manual", 0) + 1

        except Exception as e:
            print(f"❌ Error analyzing/executing alert {alert_id[:8]}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            db.close()

    def _select_cycle_nodes(self, node_ids: list) -> list:
        """Pick the rotating slice of nodes that gets a KPI row this tick.

        With interval I and cycle C, each tick covers ceil(N * C / I) nodes so
        every node is sampled once per I seconds. If C >= I every node is
        sampled every tick (legacy behaviour).
        """
        if not node_ids or self.cycle_seconds >= self.kpi_interval:
            return node_ids
        n = len(node_ids)
        per_cycle = max(1, math.ceil(n * self.cycle_seconds / self.kpi_interval))
        start = self._cycle_offset % n
        selected = node_ids[start:start + per_cycle]
        if len(selected) < per_cycle:  # wrap around
            selected = selected + node_ids[:per_cycle - len(selected)]
        self._cycle_offset = (start + per_cycle) % n
        return selected

    def _get_node_ids(self, db: Session) -> list:
        """Get node IDs with caching (refreshes every 60 seconds instead of every cycle)"""
        now = datetime.now()
        if (self._cached_node_ids
                and self._node_ids_last_refreshed
                and (now - self._node_ids_last_refreshed).total_seconds() < self._node_ids_refresh_interval):
            return self._cached_node_ids

        query = select(FiberNodeModel.node_id)
        result = db.execute(query)
        self._cached_node_ids = [row[0] for row in result.all()]
        self._node_ids_last_refreshed = now
        return self._cached_node_ids

    async def _generate_cycle(self):
        """Run one cycle of data generation"""
        import gc

        db = self.get_db()
        try:
            # Get node IDs (cached, refreshes every 60s), then the slice for this tick
            node_ids = self._select_cycle_nodes(self._get_node_ids(db))

            if not node_ids:
                return  # No nodes to generate data for

            # Get next ID for KPIs
            max_kpi_id_result = db.execute(select(func.max(KPIMetricsModel.id)))
            max_kpi_id = max_kpi_id_result.scalar() or 0

            # Get next ID for alerts
            max_alert_id_result = db.execute(select(func.max(AlertModel.id)))
            max_alert_id = max_alert_id_result.scalar() or 0

            # Get next ID for actions
            max_action_id_result = db.execute(select(func.max(SelfHealingActionModel.id)))
            max_action_id = max_action_id_result.scalar() or 0

            timestamp = datetime.now()
            alert_batch = []
            action_batch = []

            kpi_id = max_kpi_id
            alert_id = max_alert_id
            action_id = max_action_id

            # Insert KPIs in batches to avoid huge SQL statements that bloat memory.
            # A single INSERT with 7000+ rows creates a multi-MB compiled statement
            # that SQLAlchemy caches, leaking memory every cycle.
            KPI_BATCH_SIZE = 1000
            kpi_batch = []
            kpi_count = 0

            for node_id in node_ids:
                # Generate KPI for each node with weather data
                kpi_id += 1
                weather_data = self._node_weather.get(node_id)  # May be None if not fetched yet
                kpi_data = generate_node_kpi_metrics(node_id, timestamp, weather_conditions=weather_data)
                kpi_data['id'] = kpi_id
                kpi_batch.append(kpi_data)

                # Flush KPI batch when it reaches the limit
                if len(kpi_batch) >= KPI_BATCH_SIZE:
                    insert_stmt = pg_insert(KPIMetricsModel.__table__).values(kpi_batch)
                    insert_stmt = insert_stmt.on_conflict_do_nothing()
                    db.execute(insert_stmt)
                    kpi_count += len(kpi_batch)
                    kpi_batch.clear()

                # Randomly generate alerts (with low probability)
                # Weather can increase alert probability
                alert_prob = self.alert_probability
                if weather_data and weather_data.get("weather_impact", 0) > 0.3:
                    # Bad weather increases alert probability by up to 3x
                    alert_prob *= (1 + weather_data["weather_impact"] * 2)

                if random.random() < alert_prob:
                    alert_id += 1
                    alert_data = generate_cable_alert(node_id)
                    alert_data['id'] = alert_id
                    alert_data['timestamp'] = timestamp  # Use current timestamp
                    alert_data['status'] = 'ACTIVE'  # New alerts are active
                    alert_data['resolved_at'] = None  # New alerts are not resolved
                    alert_batch.append(alert_data)

                    # Generate corresponding action
                    action_id += 1
                    action_data = generate_auto_resolution_action(node_id, alert_data['alert_id'])
                    action_data['id'] = action_id
                    action_data['start_time'] = timestamp
                    action_data['status'] = 'PENDING'
                    # Clear fields that the generator randomizes but don't apply to new PENDING actions
                    action_data['end_time'] = None
                    action_data['effectiveness_score'] = None
                    action_data['ticket_id'] = None
                    action_data['escalation_reason'] = None
                    action_batch.append(action_data)

            # Flush remaining KPIs
            if kpi_batch:
                insert_stmt = pg_insert(KPIMetricsModel.__table__).values(kpi_batch)
                insert_stmt = insert_stmt.on_conflict_do_nothing()
                db.execute(insert_stmt)
                kpi_count += len(kpi_batch)
                kpi_batch.clear()

            self.stats["kpis_generated"] += kpi_count

            # Bulk insert alerts (use ON CONFLICT DO NOTHING to handle race conditions)
            if alert_batch:
                insert_stmt = pg_insert(AlertModel.__table__).values(alert_batch)
                insert_stmt = insert_stmt.on_conflict_do_nothing()
                db.execute(insert_stmt)
                self.stats["alerts_generated"] += len(alert_batch)

                # Send Slack notifications for critical alerts
                for alert_data in alert_batch:
                    if alert_data.get('severity', '').upper() == 'CRITICAL':
                        asyncio.create_task(
                            slack_service.notify_alert(
                                node_id=alert_data['node_id'],
                                alert_type=alert_data.get('type', 'UNKNOWN'),
                                severity=alert_data.get('severity', 'warning'),
                                description=alert_data.get('description', 'Alert detected'),
                                timestamp=alert_data.get('timestamp')
                            )
                        )

                # Update node status based on alert severity
                # Critical alerts -> outage, Warning alerts -> degraded
                nodes_to_outage = set()
                nodes_to_degrade = set()
                for alert_data in alert_batch:
                    severity = alert_data.get('severity', '').upper()
                    node_id = alert_data.get('node_id')
                    if severity == 'CRITICAL':
                        nodes_to_outage.add(node_id)
                    elif severity == 'WARNING':
                        nodes_to_degrade.add(node_id)

                # Remove nodes from degrade set if they're already in outage set
                nodes_to_degrade = nodes_to_degrade - nodes_to_outage

                from sqlalchemy import update as sql_update
                if nodes_to_outage:
                    update_stmt = sql_update(FiberNodeModel).where(
                        FiberNodeModel.node_id.in_(nodes_to_outage)
                    ).values(status='outage')
                    db.execute(update_stmt)

                if nodes_to_degrade:
                    # Only degrade nodes that aren't already in outage
                    update_stmt = sql_update(FiberNodeModel).where(
                        FiberNodeModel.node_id.in_(nodes_to_degrade),
                        FiberNodeModel.status != 'outage'
                    ).values(status='degraded')
                    db.execute(update_stmt)

                # Trigger autonomous AI analysis for new alerts (always-on mode)
                # Rate limited: only analyze 1 alert per cycle to prevent LLM overload
                # Also limited to max concurrent analyses to prevent memory buildup
                if alert_batch:
                    # Clean up completed tasks
                    self._pending_analysis_tasks = {t for t in self._pending_analysis_tasks if not t.done()}

                    # Only create new task if under limit
                    if len(self._pending_analysis_tasks) < self._max_concurrent_analyses:
                        first_alert = alert_batch[0]
                        task = asyncio.create_task(
                            self._analyze_and_execute_alert(
                                alert_id=first_alert['alert_id'],
                                node_id=first_alert.get('node_id'),
                                alert_type=first_alert.get('type'),
                                severity=first_alert.get('severity')
                            )
                        )
                        self._pending_analysis_tasks.add(task)
                    else:
                        # Skip this cycle - too many analyses pending
                        pass

            # Bulk insert actions (use ON CONFLICT DO NOTHING to handle race conditions)
            if action_batch:
                insert_stmt = pg_insert(SelfHealingActionModel.__table__).values(action_batch)
                insert_stmt = insert_stmt.on_conflict_do_nothing()
                db.execute(insert_stmt)
                self.stats["actions_generated"] += len(action_batch)

            db.commit()

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

        # Release memory from compiled SQL statements and batch data
        gc.collect()

    # Map action_type → number of remediation steps (must match frontend REMEDIATION_WORKFLOWS).
    # The frontend shows ~10s per step, so total visible time = steps × 10s.
    # We add ~15s of PENDING time before IN_PROGRESS starts.
    ACTION_STEP_COUNTS = {
        # Backend-generated cable network types (from constants.ACTION_TYPES)
        'MODEM_REMOTE_REBOOT': 4,
        'FIRMWARE_PUSH': 6,
        'PROVISIONING_REFRESH': 5,
        'CMTS_PORT_RESET': 6,
        'SIGNAL_LEVEL_ADJUSTMENT': 4,
        'TRAFFIC_REROUTE': 5,
        'NODE_CAPACITY_REBALANCE': 6,
        'TICKET_CREATION': 6,
        # Legacy frontend-originated types
        'NODE_REBOOT': 8,
        'LOAD_BALANCE': 7,
        'PARAMETER_OPTIMIZATION': 7,
        'TRAFFIC_REROUTING': 6,
        'RF_ADJUSTMENT': 7,
        'CAPACITY_EXPANSION': 6,
    }
    STEP_DURATION_SECONDS = 10  # Frontend uses 10s per step for visual progression
    PENDING_DURATION_SECONDS = 12  # Frontend expects ~15s; pick up a few seconds early

    async def _process_actions(self):
        """Process pending/in-progress actions to simulate self-healing with retry on conflict"""
        from sqlalchemy import update, text

        for attempt in range(MAX_RETRIES):
            db = self.get_db()
            try:
                now = datetime.now()
                updated_count = 0
                completed_count = 0

                # === PENDING -> IN_PROGRESS ===
                # Get pending actions that are old enough to potentially start
                # Limit must exceed creation rate (~58/cycle) to avoid backlog
                pending_query = select(
                    SelfHealingActionModel.id,
                    SelfHealingActionModel.start_time
                ).where(
                    SelfHealingActionModel.status == 'PENDING'
                ).order_by(SelfHealingActionModel.start_time).limit(200)
                result = db.execute(pending_query)
                pending_actions = result.all()

                # Collect action PKs to update to IN_PROGRESS
                actions_to_start = []
                for pk_id, start_time in pending_actions:
                    action_age_seconds = (now - start_time).total_seconds() if start_time else 0
                    if action_age_seconds >= self.PENDING_DURATION_SECONDS and random.random() < 0.80:
                        actions_to_start.append(pk_id)
                        updated_count += 1

                # Batch update PENDING -> IN_PROGRESS
                if actions_to_start:
                    stmt = update(SelfHealingActionModel).where(
                        SelfHealingActionModel.id.in_(actions_to_start)
                    ).values(status='IN_PROGRESS')
                    db.execute(stmt)
                    db.commit()

                # === IN_PROGRESS -> COMPLETED ===
                # Actions must stay IN_PROGRESS long enough for the frontend to
                # walk through each remediation step visually (~10s per step).
                # Fetch action_type so we can calculate per-type minimum duration.
                in_progress_query = select(
                    SelfHealingActionModel.id,
                    SelfHealingActionModel.start_time,
                    SelfHealingActionModel.action_type,
                ).where(
                    SelfHealingActionModel.status == 'IN_PROGRESS'
                ).order_by(SelfHealingActionModel.start_time).limit(200)
                result = db.execute(in_progress_query)
                in_progress_actions = result.all()

                # Collect actions to complete — only when they've been in-progress
                # long enough for all their remediation steps to finish visually.
                actions_to_complete = []
                for pk_id, start_time, action_type in in_progress_actions:
                    action_age_seconds = (now - start_time).total_seconds() if start_time else 0
                    # Time spent in IN_PROGRESS = total age minus the PENDING phase
                    in_progress_seconds = max(0, action_age_seconds - self.PENDING_DURATION_SECONDS)
                    # Minimum IN_PROGRESS duration = number of steps × seconds per step
                    step_count = self.ACTION_STEP_COUNTS.get(action_type, 3)
                    min_duration = step_count * self.STEP_DURATION_SECONDS
                    if in_progress_seconds >= min_duration and random.random() < 0.80:
                        actions_to_complete.append(pk_id)
                        completed_count += 1

                # Batch update IN_PROGRESS -> COMPLETED
                if actions_to_complete:
                    # Get alert_ids for actions we're completing (to resolve alerts)
                    alert_ids_to_resolve = []
                    action_alert_query = select(
                        SelfHealingActionModel.id,
                        SelfHealingActionModel.alert_id
                    ).where(SelfHealingActionModel.id.in_(actions_to_complete))
                    action_alerts = db.execute(action_alert_query).all()
                    action_alert_map = {row[0]: row[1] for row in action_alerts}

                    # Determine success/failure (95% success rate - increased for faster recovery)
                    failed_action_alert_ids = []  # Track alerts from failed actions for dispatch
                    for pk_id in actions_to_complete:
                        is_success = random.random() < 0.91  # ~91% success rate for demo
                        new_status = 'COMPLETED' if is_success else 'FAILED'
                        effectiveness = random.uniform(0.75, 1.0) if is_success else random.uniform(0.0, 0.3)

                        stmt = update(SelfHealingActionModel).where(
                            SelfHealingActionModel.id == pk_id
                        ).values(
                            status=new_status,
                            end_time=now,
                            effectiveness_score=round(effectiveness, 2)
                        )
                        db.execute(stmt)

                        # If action completed successfully, resolve the associated alert
                        if is_success and pk_id in action_alert_map:
                            alert_id = action_alert_map[pk_id]
                            if alert_id:
                                alert_ids_to_resolve.append(alert_id)
                        # If action failed, track for dispatch ticket creation
                        elif not is_success and pk_id in action_alert_map:
                            alert_id = action_alert_map[pk_id]
                            if alert_id:
                                failed_action_alert_ids.append(alert_id)

                    # Import sql_update before either conditional block needs it
                    from sqlalchemy import update as sql_update

                    # Resolve alerts for successfully completed actions
                    if alert_ids_to_resolve:
                        # First, get node_ids for the alerts being resolved
                        node_ids_query = select(AlertModel.node_id).where(
                            AlertModel.alert_id.in_(alert_ids_to_resolve)
                        ).distinct()
                        node_ids_result = db.execute(node_ids_query).fetchall()
                        affected_node_ids = [row[0] for row in node_ids_result]

                        # Resolve the alerts
                        resolve_stmt = sql_update(AlertModel).where(
                            AlertModel.alert_id.in_(alert_ids_to_resolve),
                            AlertModel.status == 'ACTIVE'
                        ).values(
                            status='RESOLVED',
                            resolved_at=now
                        )
                        db.execute(resolve_stmt)

                        # Update node status based on remaining active alerts
                        # For each affected node, check if it has any remaining active alerts
                        for node_id in affected_node_ids:
                            # Check for remaining active critical alerts (handle both cases)
                            critical_count = db.execute(
                                select(func.count(AlertModel.id)).where(
                                    AlertModel.node_id == node_id,
                                    AlertModel.status == 'ACTIVE',
                                    AlertModel.severity.in_(['CRITICAL', 'critical'])
                                )
                            ).scalar() or 0

                            # Check for remaining active warning alerts (handle both cases)
                            warning_count = db.execute(
                                select(func.count(AlertModel.id)).where(
                                    AlertModel.node_id == node_id,
                                    AlertModel.status == 'ACTIVE',
                                    AlertModel.severity.in_(['WARNING', 'warning'])
                                )
                            ).scalar() or 0

                            # Determine new status based on remaining alerts
                            if critical_count > 0:
                                new_status = 'outage'
                            elif warning_count > 0:
                                new_status = 'degraded'
                            else:
                                new_status = 'healthy'

                            # Update node status
                            update_node_stmt = sql_update(FiberNodeModel).where(
                                FiberNodeModel.node_id == node_id
                            ).values(status=new_status)
                            db.execute(update_node_stmt)

                    # Handle failed actions: create dispatch tickets and resolve alerts
                    if failed_action_alert_ids:
                        # Get alert details for dispatch tickets
                        failed_alerts_query = select(
                            AlertModel.alert_id,
                            AlertModel.node_id,
                            AlertModel.type,
                            AlertModel.severity,
                            AlertModel.description
                        ).where(
                            AlertModel.alert_id.in_(failed_action_alert_ids),
                            AlertModel.status == 'ACTIVE'
                        )
                        failed_alerts = db.execute(failed_alerts_query).all()

                        # Get next available ID for dispatch tickets
                        max_action_id_result = db.execute(select(func.max(SelfHealingActionModel.id)))
                        next_action_id = (max_action_id_result.scalar() or 0) + 1

                        dispatch_tickets = []
                        failed_node_ids = set()
                        for alert_id, node_id, alert_type, severity, description in failed_alerts:
                            failed_node_ids.add(node_id)
                            # Create dispatch ticket for each failed alert
                            ticket_id = f"DISPATCH-{uuid.uuid4().hex[:8].upper()}"
                            dispatch_tickets.append({
                                'id': next_action_id,
                                'action_id': ticket_id,
                                'node_id': node_id,
                                'alert_id': alert_id,
                                'action_type': 'TICKET_CREATION',
                                'description': f"[Auto-Dispatch] Automated healing failed for {alert_type}. {description or 'Manual intervention required.'}",
                                'status': 'PENDING',
                                'start_time': now,
                                'effectiveness_score': 0.0
                            })
                            next_action_id += 1

                        # Bulk insert dispatch tickets (use ON CONFLICT DO NOTHING to handle race conditions)
                        if dispatch_tickets:
                            insert_stmt = pg_insert(SelfHealingActionModel.__table__).values(dispatch_tickets)
                            insert_stmt = insert_stmt.on_conflict_do_nothing()
                            db.execute(insert_stmt)
                            print(f"🎫 Created {len(dispatch_tickets)} dispatch tickets for failed healing actions")

                        # Resolve the failed alerts (they now have dispatch tickets)
                        resolve_failed_stmt = sql_update(AlertModel).where(
                            AlertModel.alert_id.in_(failed_action_alert_ids),
                            AlertModel.status == 'ACTIVE'
                        ).values(
                            status='RESOLVED',
                            resolved_at=now
                        )
                        db.execute(resolve_failed_stmt)

                        # Update node status for affected nodes
                        for node_id in failed_node_ids:
                            critical_count = db.execute(
                                select(func.count(AlertModel.id)).where(
                                    AlertModel.node_id == node_id,
                                    AlertModel.status == 'ACTIVE',
                                    AlertModel.severity.in_(['CRITICAL', 'critical'])
                                )
                            ).scalar() or 0

                            warning_count = db.execute(
                                select(func.count(AlertModel.id)).where(
                                    AlertModel.node_id == node_id,
                                    AlertModel.status == 'ACTIVE',
                                    AlertModel.severity.in_(['WARNING', 'warning'])
                                )
                            ).scalar() or 0

                            if critical_count > 0:
                                new_status = 'outage'
                            elif warning_count > 0:
                                new_status = 'degraded'
                            else:
                                new_status = 'healthy'

                            update_node_stmt = sql_update(FiberNodeModel).where(
                                FiberNodeModel.node_id == node_id
                            ).values(status=new_status)
                            db.execute(update_node_stmt)

                    db.commit()

                # Import sql_update for node status updates (may not be imported if no actions completed above)
                from sqlalchemy import update as sql_update

                # === DISPATCH TICKETS (TICKET_CREATION) -> COMPLETED ===
                # Process dispatch tickets - these represent field technician interventions
                # They take longer but always succeed (technicians fix the issue)
                dispatch_query = select(
                    SelfHealingActionModel.id,
                    SelfHealingActionModel.node_id,
                    SelfHealingActionModel.start_time
                ).where(
                    SelfHealingActionModel.status.in_(['PENDING', 'IN_PROGRESS']),
                    SelfHealingActionModel.action_type == 'TICKET_CREATION'
                ).order_by(SelfHealingActionModel.start_time).limit(50)
                dispatch_result = db.execute(dispatch_query)
                dispatch_tickets = dispatch_result.all()

                dispatches_to_complete = []
                eligible_dispatch_count = 0
                for pk_id, node_id, start_time in dispatch_tickets:
                    ticket_age_seconds = (now - start_time).total_seconds() if start_time else 0
                    # Dispatch tickets complete after 60-120 seconds (simulating technician travel + work)
                    # 25% chance per cycle after 45 seconds (increased for faster recovery)
                    if ticket_age_seconds >= 45:
                        eligible_dispatch_count += 1
                        if random.random() < 0.25:
                            dispatches_to_complete.append((pk_id, node_id))

                # Log dispatch ticket status
                if dispatch_tickets:
                    print(f"📋 Dispatch tickets: {len(dispatch_tickets)} pending/in-progress, {eligible_dispatch_count} eligible (>45s old)")

                # Complete dispatch tickets and heal nodes
                if dispatches_to_complete:
                    node_ids_healed = set()
                    for pk_id, node_id in dispatches_to_complete:
                        # Mark dispatch as completed with high effectiveness (technician fixed it)
                        stmt = update(SelfHealingActionModel).where(
                            SelfHealingActionModel.id == pk_id
                        ).values(
                            status='COMPLETED',
                            end_time=now,
                            effectiveness_score=0.95  # Technicians are effective
                        )
                        db.execute(stmt)
                        node_ids_healed.add(node_id)

                    # Heal nodes that had dispatch tickets completed
                    for node_id in node_ids_healed:
                        # Check for remaining active alerts (shouldn't be any, but check anyway)
                        critical_count = db.execute(
                            select(func.count(AlertModel.id)).where(
                                AlertModel.node_id == node_id,
                                AlertModel.status == 'ACTIVE',
                                AlertModel.severity.in_(['CRITICAL', 'critical'])
                            )
                        ).scalar() or 0

                        warning_count = db.execute(
                            select(func.count(AlertModel.id)).where(
                                AlertModel.node_id == node_id,
                                AlertModel.status == 'ACTIVE',
                                AlertModel.severity.in_(['WARNING', 'warning'])
                            )
                        ).scalar() or 0

                        # Only set to healthy if no active alerts
                        if critical_count == 0 and warning_count == 0:
                            update_node_stmt = sql_update(FiberNodeModel).where(
                                FiberNodeModel.node_id == node_id
                            ).values(status='healthy')
                            db.execute(update_node_stmt)

                    if dispatches_to_complete:
                        print(f"👷 {len(dispatches_to_complete)} dispatch tickets completed by field technicians")
                    db.commit()

                # === CLEANUP STALE ALERTS ===
                # Resolve alerts that have been active for too long (> 2 minutes)
                # This prevents alert backlog from blocking node recovery
                stale_cutoff = now - timedelta(minutes=2)
                stale_alerts_stmt = sql_update(AlertModel).where(
                    AlertModel.status.in_(['ACTIVE', 'active', 'Active']),
                    AlertModel.timestamp < stale_cutoff
                ).values(
                    status='RESOLVED',
                    resolved_at=now
                )
                stale_result = db.execute(stale_alerts_stmt)
                stale_count = stale_result.rowcount
                if stale_count > 0:
                    db.commit()
                    print(f"🧹 Cleaned up {stale_count} stale alerts (>2 min old)")

                # === NATURAL RECOVERY for unhealthy nodes without active alerts ===
                # Nodes that are degraded/outage but have no active alerts should recover

                # Debug: count total active alerts
                total_active_alerts = db.execute(
                    select(func.count(AlertModel.id)).where(
                        AlertModel.status.in_(['ACTIVE', 'active', 'Active'])
                    )
                ).scalar() or 0

                unhealthy_nodes_query = select(
                    FiberNodeModel.node_id
                ).where(
                    FiberNodeModel.status.in_(['outage', 'degraded', 'maintenance'])
                ).limit(100)
                unhealthy_result = db.execute(unhealthy_nodes_query)
                unhealthy_nodes = [row[0] for row in unhealthy_result.all()]

                nodes_to_heal = []
                nodes_no_alerts = 0
                for node_id in unhealthy_nodes:
                    # Check for active alerts (case-insensitive status check)
                    active_alert_count = db.execute(
                        select(func.count(AlertModel.id)).where(
                            AlertModel.node_id == node_id,
                            AlertModel.status.in_(['ACTIVE', 'active', 'Active'])
                        )
                    ).scalar() or 0

                    if active_alert_count == 0:
                        nodes_no_alerts += 1
                        # No active alerts - node should recover
                        # 25% chance per cycle for natural recovery (increased for faster healing)
                        if random.random() < 0.25:
                            nodes_to_heal.append(node_id)

                # Log status every time
                if unhealthy_nodes:
                    print(f"🏥 Natural recovery: {len(unhealthy_nodes)} unhealthy, {nodes_no_alerts} without alerts (total active alerts: {total_active_alerts}), {len(nodes_to_heal)} recovering")

                if nodes_to_heal:
                    heal_stmt = sql_update(FiberNodeModel).where(
                        FiberNodeModel.node_id.in_(nodes_to_heal)
                    ).values(status='healthy')
                    db.execute(heal_stmt)
                    db.commit()
                    print(f"🔧 {len(nodes_to_heal)} nodes naturally recovered to healthy")

                # Success - exit retry loop
                return

            except OperationalError as e:
                db.rollback()
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                print(f"Error processing actions (attempt {attempt + 1}): {e}")
            except Exception as e:
                db.rollback()
                print(f"Error processing actions: {e}")
                import traceback
                traceback.print_exc()
                return
            finally:
                db.close()

    def get_stats(self) -> dict:
        """Get generation statistics"""
        # Clean up completed tasks before counting
        self._pending_analysis_tasks = {t for t in self._pending_analysis_tasks if not t.done()}
        return {
            **self.stats,
            "running": self.running,
            "paused": self.paused,
            "pending_analysis_tasks": len(self._pending_analysis_tasks),
            "max_concurrent_analyses": self._max_concurrent_analyses,
            # AI optimization settings
            "ai_optimization": {
                "llm_sample_rate": self.llm_sample_rate,
                "node_cooldown_minutes": self.node_cooldown_minutes,
                "cache_ttl_minutes": self._cache_ttl_minutes,
                "cache_size": len(self._analysis_cache),
                "nodes_on_cooldown": len(self._node_last_analyzed),
            },
        }

    def get_ai_optimization_settings(self) -> dict:
        """Get current AI optimization settings"""
        return {
            "llm_sample_rate": self.llm_sample_rate,
            "node_cooldown_minutes": self.node_cooldown_minutes,
            "cache_ttl_minutes": self._cache_ttl_minutes,
            "cache_size": len(self._analysis_cache),
            "nodes_on_cooldown": len(self._node_last_analyzed),
        }

    def set_ai_optimization_settings(
        self,
        llm_sample_rate: int = None,
        node_cooldown_minutes: int = None,
        cache_ttl_minutes: int = None,
    ) -> dict:
        """
        Update AI optimization settings.

        Args:
            llm_sample_rate: Use LLM for 1 in N alerts (higher = less AI usage)
            node_cooldown_minutes: Minutes before re-analyzing same node
            cache_ttl_minutes: How long to cache analysis results

        Returns:
            Updated settings
        """
        if llm_sample_rate is not None and llm_sample_rate >= 1:
            self.llm_sample_rate = llm_sample_rate
            print(f"🔧 AI optimization: llm_sample_rate = {llm_sample_rate}")

        if node_cooldown_minutes is not None and node_cooldown_minutes >= 0:
            self.node_cooldown_minutes = node_cooldown_minutes
            print(f"🔧 AI optimization: node_cooldown_minutes = {node_cooldown_minutes}")

        if cache_ttl_minutes is not None and cache_ttl_minutes >= 0:
            self._cache_ttl_minutes = cache_ttl_minutes
            print(f"🔧 AI optimization: cache_ttl_minutes = {cache_ttl_minutes}")

        return self.get_ai_optimization_settings()

    def clear_ai_caches(self):
        """Clear all AI optimization caches"""
        self._analysis_cache.clear()
        self._node_last_analyzed.clear()
        print("🧹 AI caches cleared")
        return {"cleared": True}


# Singleton instance
background_generator = BackgroundDataGenerator()
