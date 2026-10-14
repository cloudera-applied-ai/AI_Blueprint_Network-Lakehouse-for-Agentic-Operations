"""
Data Retention Service - Tiered data rollup and cleanup

Retention Policy:
- Raw (one sample per node per KPI_GENERATION_INTERVAL_SECONDS): keep RETENTION_RAW_HOURS (default 2h)
- 1-minute: Keep 6 hours, then aggregate to 5-min
- 5-minute: Keep 12 hours (RETENTION_5MIN_HOURS), then aggregate to hourly
- Hourly: Keep 3 days (RETENTION_HOURLY_DAYS), then aggregate to daily
- Daily: Keep 30 days, then delete

This reduces storage from ~34.5M records/day to ~3.1M records max.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, delete, text
from sqlalchemy.exc import OperationalError

from .config import settings
from .database import SessionLocal
from .models import (
    KPIMetricsModel,
    KPIMetrics1MinModel,
    KPIMetrics5MinModel,
    KPIMetricsHourlyModel,
    KPIMetricsDailyModel,
    AlertModel,
    SelfHealingActionModel,
)

# Retention periods - configurable via env vars / application/.env (see config.py).
# Defaults keep a laptop deployment well under 1 GB.
RETENTION_RAW = timedelta(hours=settings.RETENTION_RAW_HOURS)
RETENTION_1MIN = timedelta(hours=settings.RETENTION_1MIN_HOURS)
RETENTION_5MIN = timedelta(hours=settings.RETENTION_5MIN_HOURS)
RETENTION_HOURLY = timedelta(days=settings.RETENTION_HOURLY_DAYS)
RETENTION_DAILY = timedelta(days=settings.RETENTION_DAILY_DAYS)

# Alert/Action retention
RETENTION_RESOLVED_ALERTS = timedelta(days=settings.RETENTION_RESOLVED_ALERTS_DAYS)
RETENTION_COMPLETED_ACTIONS = timedelta(days=settings.RETENTION_COMPLETED_ACTIONS_DAYS)

# Rollup intervals (how often to run each rollup)
ROLLUP_INTERVAL_1MIN = 60           # Every 60 seconds
ROLLUP_INTERVAL_5MIN = 300          # Every 5 minutes
ROLLUP_INTERVAL_HOURLY = 3600       # Every hour
ROLLUP_INTERVAL_DAILY = 86400       # Every day
CLEANUP_INTERVAL = 300              # Cleanup every 5 minutes


class DataRetentionService:
    """Background service for data rollup and cleanup"""

    def __init__(self):
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.last_rollup_1min = datetime.min
        self.last_rollup_5min = datetime.min
        self.last_rollup_hourly = datetime.min
        self.last_rollup_daily = datetime.min
        self.last_cleanup = datetime.min
        self.stats = {
            "rollups_1min": 0,
            "rollups_5min": 0,
            "rollups_hourly": 0,
            "rollups_daily": 0,
            "records_deleted": 0,
            "last_run": None,
        }

    def get_db(self) -> Session:
        return SessionLocal()

    async def start(self):
        """Start the data retention service"""
        if self.running:
            print("[WARN] Data retention service already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._run_loop())
        print("[INFO] Data retention service started")

    async def stop(self):
        """Stop the data retention service"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        print("[INFO] Data retention service stopped")

    async def _run_loop(self):
        """Main loop - check for rollup and cleanup tasks"""
        # Wait for the background generator to finish initial data loading before
        # running heavy rollup/cleanup queries.  This prevents the data retention
        # service from overwhelming PostgreSQL at startup (all intervals would
        # fire simultaneously because last_* times default to datetime.min).
        from .background_tasks import background_generator
        while not getattr(background_generator, 'data_ready', False) and self.running:
            await asyncio.sleep(2)

        # Stagger first run: set last_* to now so intervals start fresh
        # instead of all firing at once (they were datetime.min).
        now = datetime.now()
        self.last_rollup_1min = now
        self.last_rollup_5min = now
        self.last_rollup_hourly = now
        self.last_rollup_daily = now
        self.last_cleanup = now
        print("[INFO] Data retention service ready (intervals staggered from now)")

        while self.running:
            try:
                now = datetime.now()

                # 1-minute rollup (every 60 seconds)
                if (now - self.last_rollup_1min).total_seconds() >= ROLLUP_INTERVAL_1MIN:
                    await self._rollup_to_1min()
                    self.last_rollup_1min = now

                # 5-minute rollup (every 5 minutes)
                if (now - self.last_rollup_5min).total_seconds() >= ROLLUP_INTERVAL_5MIN:
                    await self._rollup_to_5min()
                    self.last_rollup_5min = now

                # Hourly rollup (every hour)
                if (now - self.last_rollup_hourly).total_seconds() >= ROLLUP_INTERVAL_HOURLY:
                    await self._rollup_to_hourly()
                    self.last_rollup_hourly = now

                # Daily rollup (every day)
                if (now - self.last_rollup_daily).total_seconds() >= ROLLUP_INTERVAL_DAILY:
                    await self._rollup_to_daily()
                    self.last_rollup_daily = now

                # Cleanup old data (every 5 minutes)
                if (now - self.last_cleanup).total_seconds() >= CLEANUP_INTERVAL:
                    await self._cleanup_old_data()
                    self.last_cleanup = now

                self.stats["last_run"] = now.isoformat()

            except Exception as e:
                print(f"[ERROR] Data retention error: {e}")
                import traceback
                traceback.print_exc()

            await asyncio.sleep(30)  # Check every 30 seconds

    async def _rollup_to_1min(self):
        """Aggregate raw data (older than 1 min) into 1-minute buckets"""
        db = self.get_db()
        try:
            now = datetime.now()
            # Aggregate data from 2 minutes ago to 1 minute ago (complete minute)
            end_time = now.replace(second=0, microsecond=0) - timedelta(minutes=1)
            start_time = end_time - timedelta(minutes=1)

            # Get max ID for new records
            max_id_result = db.execute(select(func.max(KPIMetrics1MinModel.id)))
            max_id = max_id_result.scalar() or 0

            # Use PostgreSQL's date_trunc for efficient aggregation
            query = text("""
                INSERT INTO kpi_metrics_1min (
                    id, node_id, timestamp, sample_count,
                    ds_snr_db, us_snr_db, ds_power_level_dbmv,
                    us_power_level_dbmv, latency_ms, packet_loss_percent, downstream_throughput_mbps,
                    active_modems, node_cpu_utilization, node_memory_utilization, node_temperature,
                    latency_max, cpu_max, temperature_max
                )
                SELECT
                    ROW_NUMBER() OVER () + :max_id as id,
                    node_id,
                    date_trunc('minute', timestamp) as timestamp,
                    COUNT(*) as sample_count,
                    AVG(ds_snr_db),
                    AVG(us_snr_db),
                    AVG(ds_power_level_dbmv),
                    AVG(us_power_level_dbmv),
                    AVG(latency_ms),
                    AVG(packet_loss_percent),
                    AVG(downstream_throughput_mbps),
                    AVG(active_modems),
                    AVG(node_cpu_utilization),
                    AVG(node_memory_utilization),
                    AVG(node_temperature),
                    MAX(latency_ms),
                    MAX(node_cpu_utilization),
                    MAX(node_temperature)
                FROM kpi_metrics
                WHERE timestamp >= :start_time AND timestamp < :end_time
                GROUP BY node_id, date_trunc('minute', timestamp)
                ON CONFLICT DO NOTHING
            """)

            result = db.execute(query, {
                "max_id": max_id,
                "start_time": start_time,
                "end_time": end_time
            })
            db.commit()

            self.stats["rollups_1min"] += 1

        except Exception as e:
            db.rollback()
            # Don't spam logs for empty rollups
            if "ON CONFLICT" not in str(e):
                print(f"1-min rollup error: {e}")
        finally:
            db.close()

    async def _rollup_to_5min(self):
        """Aggregate 1-minute data into 5-minute buckets"""
        db = self.get_db()
        try:
            now = datetime.now()
            # Round down to nearest 5 minutes
            minute = (now.minute // 5) * 5
            end_time = now.replace(minute=minute, second=0, microsecond=0) - timedelta(minutes=5)
            start_time = end_time - timedelta(minutes=5)

            max_id_result = db.execute(select(func.max(KPIMetrics5MinModel.id)))
            max_id = max_id_result.scalar() or 0

            # Aggregate from 1-min table using standard PostgreSQL (no TimescaleDB)
            # 5-minute bucket: date_trunc('hour', ts) + interval '5 min' * (extract(minute from ts)::int / 5)
            query = text("""
                INSERT INTO kpi_metrics_5min (
                    id, node_id, timestamp, sample_count,
                    ds_snr_db, us_snr_db, ds_power_level_dbmv,
                    us_power_level_dbmv, latency_ms, packet_loss_percent, downstream_throughput_mbps,
                    active_modems, node_cpu_utilization, node_memory_utilization, node_temperature,
                    latency_max, cpu_max, temperature_max
                )
                SELECT
                    ROW_NUMBER() OVER () + :max_id as id,
                    node_id,
                    date_trunc('hour', timestamp) + INTERVAL '5 minutes' * (EXTRACT(MINUTE FROM timestamp)::int / 5) as time_bucket,
                    SUM(sample_count) as sample_count,
                    AVG(ds_snr_db),
                    AVG(us_snr_db),
                    AVG(ds_power_level_dbmv),
                    AVG(us_power_level_dbmv),
                    AVG(latency_ms),
                    AVG(packet_loss_percent),
                    AVG(downstream_throughput_mbps),
                    AVG(active_modems),
                    AVG(node_cpu_utilization),
                    AVG(node_memory_utilization),
                    AVG(node_temperature),
                    MAX(latency_max),
                    MAX(cpu_max),
                    MAX(temperature_max)
                FROM kpi_metrics_1min
                WHERE timestamp >= :start_time AND timestamp < :end_time
                GROUP BY node_id, date_trunc('hour', timestamp) + INTERVAL '5 minutes' * (EXTRACT(MINUTE FROM timestamp)::int / 5)
                ON CONFLICT DO NOTHING
            """)

            db.execute(query, {
                "max_id": max_id,
                "start_time": start_time,
                "end_time": end_time
            })
            db.commit()

            self.stats["rollups_5min"] += 1

        except Exception as e:
            db.rollback()
            print(f"5-min rollup error: {e}")
        finally:
            db.close()

    async def _rollup_to_hourly(self):
        """Aggregate 5-minute data into hourly buckets"""
        db = self.get_db()
        try:
            now = datetime.now()
            end_time = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
            start_time = end_time - timedelta(hours=1)

            max_id_result = db.execute(select(func.max(KPIMetricsHourlyModel.id)))
            max_id = max_id_result.scalar() or 0

            query = text("""
                INSERT INTO kpi_metrics_hourly (
                    id, node_id, timestamp, sample_count,
                    ds_snr_db, us_snr_db, ds_power_level_dbmv,
                    us_power_level_dbmv, latency_ms, packet_loss_percent, downstream_throughput_mbps,
                    active_modems, node_cpu_utilization, node_memory_utilization, node_temperature,
                    latency_max, cpu_max, temperature_max
                )
                SELECT
                    ROW_NUMBER() OVER () + :max_id as id,
                    node_id,
                    date_trunc('hour', timestamp) as timestamp,
                    SUM(sample_count) as sample_count,
                    AVG(ds_snr_db),
                    AVG(us_snr_db),
                    AVG(ds_power_level_dbmv),
                    AVG(us_power_level_dbmv),
                    AVG(latency_ms),
                    AVG(packet_loss_percent),
                    AVG(downstream_throughput_mbps),
                    AVG(active_modems),
                    AVG(node_cpu_utilization),
                    AVG(node_memory_utilization),
                    AVG(node_temperature),
                    MAX(latency_max),
                    MAX(cpu_max),
                    MAX(temperature_max)
                FROM kpi_metrics_5min
                WHERE timestamp >= :start_time AND timestamp < :end_time
                GROUP BY node_id, date_trunc('hour', timestamp)
                ON CONFLICT DO NOTHING
            """)

            db.execute(query, {
                "max_id": max_id,
                "start_time": start_time,
                "end_time": end_time
            })
            db.commit()

            self.stats["rollups_hourly"] += 1
            print(f"[INFO] Hourly rollup completed for {start_time} to {end_time}")

        except Exception as e:
            db.rollback()
            if "ON CONFLICT" not in str(e):
                print(f"Hourly rollup error: {e}")
        finally:
            db.close()

    async def _rollup_to_daily(self):
        """Aggregate hourly data into daily buckets"""
        db = self.get_db()
        try:
            now = datetime.now()
            end_time = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
            start_time = end_time - timedelta(days=1)

            max_id_result = db.execute(select(func.max(KPIMetricsDailyModel.id)))
            max_id = max_id_result.scalar() or 0

            query = text("""
                INSERT INTO kpi_metrics_daily (
                    id, node_id, timestamp, sample_count,
                    ds_snr_db, us_snr_db, ds_power_level_dbmv,
                    us_power_level_dbmv, latency_ms, packet_loss_percent, downstream_throughput_mbps,
                    active_modems, node_cpu_utilization, node_memory_utilization, node_temperature,
                    latency_max, cpu_max, temperature_max
                )
                SELECT
                    ROW_NUMBER() OVER () + :max_id as id,
                    node_id,
                    date_trunc('day', timestamp) as timestamp,
                    SUM(sample_count) as sample_count,
                    AVG(ds_snr_db),
                    AVG(us_snr_db),
                    AVG(ds_power_level_dbmv),
                    AVG(us_power_level_dbmv),
                    AVG(latency_ms),
                    AVG(packet_loss_percent),
                    AVG(downstream_throughput_mbps),
                    AVG(active_modems),
                    AVG(node_cpu_utilization),
                    AVG(node_memory_utilization),
                    AVG(node_temperature),
                    MAX(latency_max),
                    MAX(cpu_max),
                    MAX(temperature_max)
                FROM kpi_metrics_hourly
                WHERE timestamp >= :start_time AND timestamp < :end_time
                GROUP BY node_id, date_trunc('day', timestamp)
                ON CONFLICT DO NOTHING
            """)

            db.execute(query, {
                "max_id": max_id,
                "start_time": start_time,
                "end_time": end_time
            })
            db.commit()

            self.stats["rollups_daily"] += 1
            print(f"[INFO] Daily rollup completed for {start_time.date()}")

        except Exception as e:
            db.rollback()
            if "ON CONFLICT" not in str(e):
                print(f"Daily rollup error: {e}")
        finally:
            db.close()

    async def _cleanup_old_data(self):
        """Delete data older than retention periods using batched deletes to avoid table locks"""
        db = self.get_db()
        total_deleted = 0
        BATCH_LIMIT = 10000  # Delete in batches to avoid long table locks

        try:
            now = datetime.now()

            # Batched delete for raw KPIs (largest table, most critical to batch)
            raw_cutoff = now - RETENTION_RAW
            raw_deleted = 0
            while True:
                # Use subquery to select IDs for batched deletion
                ids_to_delete = db.execute(
                    select(KPIMetricsModel.id).where(
                        KPIMetricsModel.timestamp < raw_cutoff
                    ).limit(BATCH_LIMIT)
                ).scalars().all()
                if not ids_to_delete:
                    break
                db.execute(
                    delete(KPIMetricsModel).where(KPIMetricsModel.id.in_(ids_to_delete))
                )
                db.commit()
                raw_deleted += len(ids_to_delete)
                if len(ids_to_delete) < BATCH_LIMIT:
                    break
                await asyncio.sleep(0.1)  # Yield between batches
            total_deleted += raw_deleted

            # Delete 1-min aggregates (smaller tables, single delete is fine)
            min1_cutoff = now - RETENTION_1MIN
            result = db.execute(
                delete(KPIMetrics1MinModel).where(KPIMetrics1MinModel.timestamp < min1_cutoff)
            )
            total_deleted += result.rowcount

            # Delete 5-min aggregates
            min5_cutoff = now - RETENTION_5MIN
            result = db.execute(
                delete(KPIMetrics5MinModel).where(KPIMetrics5MinModel.timestamp < min5_cutoff)
            )
            total_deleted += result.rowcount

            # Delete hourly aggregates
            hourly_cutoff = now - RETENTION_HOURLY
            result = db.execute(
                delete(KPIMetricsHourlyModel).where(KPIMetricsHourlyModel.timestamp < hourly_cutoff)
            )
            total_deleted += result.rowcount

            # Delete daily aggregates
            daily_cutoff = now - RETENTION_DAILY
            result = db.execute(
                delete(KPIMetricsDailyModel).where(KPIMetricsDailyModel.timestamp < daily_cutoff)
            )
            total_deleted += result.rowcount

            # Delete resolved alerts
            alert_cutoff = now - RETENTION_RESOLVED_ALERTS
            result = db.execute(
                delete(AlertModel).where(
                    AlertModel.status == 'RESOLVED',
                    AlertModel.resolved_at < alert_cutoff
                )
            )
            total_deleted += result.rowcount

            # Delete completed/failed actions
            action_cutoff = now - RETENTION_COMPLETED_ACTIONS
            result = db.execute(
                delete(SelfHealingActionModel).where(
                    SelfHealingActionModel.status.in_(['COMPLETED', 'FAILED']),
                    SelfHealingActionModel.end_time < action_cutoff
                )
            )
            total_deleted += result.rowcount

            db.commit()

            self.stats["records_deleted"] += total_deleted

            if total_deleted > 0:
                print(f"[INFO] Cleanup: deleted {total_deleted} old records (raw KPIs: {raw_deleted})")

        except Exception as e:
            db.rollback()
            print(f"Cleanup error: {e}")
        finally:
            db.close()

    def get_stats(self) -> dict:
        """Get retention service statistics"""
        return {
            **self.stats,
            "running": self.running,
            "retention_policy": {
                "raw_hours": RETENTION_RAW.total_seconds() / 3600,
                "1min_hours": RETENTION_1MIN.total_seconds() / 3600,
                "5min_hours": RETENTION_5MIN.total_seconds() / 3600,
                "hourly_days": RETENTION_HOURLY.days,
                "daily_days": RETENTION_DAILY.days,
            }
        }


# Singleton instance
data_retention_service = DataRetentionService()
