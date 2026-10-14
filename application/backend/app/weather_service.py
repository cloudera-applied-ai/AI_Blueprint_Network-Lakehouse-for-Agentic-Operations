"""
Live Weather Service - Fetches real-time weather data for cable plant locations.

Uses Open-Meteo API (free, no API key required) to get current weather conditions
and applies them to KPI generation for realistic network behavior simulation.

Weather impacts on cable plant (HFC) performance:
- Rain: RF signal attenuation on OFDM channels, moisture ingress into connectors
- High temperature: Node/amplifier thermal throttling, increased modem flaps
- Wind: Aerial cable sway causing signal fluctuations, connector stress
- Snow/Ice: Ice loading on aerial plant, connector icing, power outage risk
- Humidity: Connector corrosion, moisture ingress into amplifiers
- Storms: Multiple compounding effects, possible plant damage, power outages
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass, field
import math
import time


@dataclass
class WeatherConditions:
    """Current weather conditions for a location"""
    latitude: float
    longitude: float
    temperature_c: float
    humidity_percent: float
    precipitation_mm: float  # Rain/snow in mm
    wind_speed_kmh: float
    wind_gusts_kmh: float
    cloud_cover_percent: float
    weather_code: int  # WMO weather code
    is_day: bool
    timestamp: datetime = field(default_factory=datetime.now)

    # Derived impact factors (0.0 = no impact, 1.0 = severe impact)
    @property
    def rain_impact(self) -> float:
        """Rain impact on signal (0-1). Heavy rain attenuates RF signals and risks moisture ingress."""
        if self.precipitation_mm <= 0:
            return 0.0
        elif self.precipitation_mm < 2.5:  # Light rain
            return 0.1
        elif self.precipitation_mm < 7.5:  # Moderate rain
            return 0.3
        elif self.precipitation_mm < 15:   # Heavy rain
            return 0.6
        else:  # Very heavy rain
            return 0.9

    @property
    def temperature_impact(self) -> float:
        """Temperature impact on equipment (0-1). Extreme temps cause issues."""
        if 10 <= self.temperature_c <= 30:
            return 0.0  # Optimal range
        elif self.temperature_c < 0:  # Freezing
            return min(0.5, abs(self.temperature_c) / 20)
        elif self.temperature_c > 35:  # Hot
            return min(0.8, (self.temperature_c - 35) / 15)
        else:
            return 0.1  # Mild impact

    @property
    def wind_impact(self) -> float:
        """Wind impact on aerial cable plant (0-1). High winds cause cable sway and connector stress."""
        if self.wind_speed_kmh < 20:
            return 0.0
        elif self.wind_speed_kmh < 40:
            return 0.2
        elif self.wind_speed_kmh < 60:
            return 0.4
        elif self.wind_speed_kmh < 80:
            return 0.6
        else:
            return 0.9

    @property
    def storm_impact(self) -> float:
        """Storm conditions based on WMO weather code"""
        # WMO codes: 95-99 are thunderstorms
        if 95 <= self.weather_code <= 99:
            return 0.8
        # 80-84 are rain showers
        elif 80 <= self.weather_code <= 84:
            return 0.4
        # 70-77 are snow
        elif 70 <= self.weather_code <= 77:
            return 0.5
        # 50-59 are drizzle
        elif 50 <= self.weather_code <= 59:
            return 0.2
        return 0.0

    @property
    def overall_impact(self) -> float:
        """Combined weather impact factor (0-1)"""
        # Weighted combination of all factors
        return min(1.0, (
            self.rain_impact * 0.35 +
            self.temperature_impact * 0.25 +
            self.wind_impact * 0.25 +
            self.storm_impact * 0.15
        ))

    def get_weather_description(self) -> str:
        """Human-readable weather description from WMO code"""
        descriptions = {
            0: "Clear sky",
            1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Foggy", 48: "Depositing rime fog",
            51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
            61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
            77: "Snow grains",
            80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
            85: "Slight snow showers", 86: "Heavy snow showers",
            95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
        }
        return descriptions.get(self.weather_code, f"Weather code {self.weather_code}")


class WeatherService:
    """
    Service for fetching and caching live weather data.

    Uses Open-Meteo API which is free and requires no API key.
    Caches weather data to avoid excessive API calls.
    Includes rate limiting and exponential backoff to respect API limits.
    """

    # Open-Meteo API endpoint
    API_URL = "https://api.open-meteo.com/v1/forecast"

    # Cache settings
    CACHE_TTL_MINUTES = 15  # Weather data cached for 15 minutes
    MAX_CACHE_SIZE = 500    # Max number of cached locations

    # Rate limiting settings (Open-Meteo free tier: ~10,000 requests/day)
    MAX_REQUESTS_PER_MINUTE = 30  # Conservative limit
    MIN_REQUEST_INTERVAL = 2.0    # Minimum seconds between requests
    MAX_RETRIES = 3               # Max retries on 429 errors
    BACKOFF_BASE = 5.0            # Base backoff time in seconds

    def __init__(self):
        self._cache: Dict[str, Tuple[WeatherConditions, datetime]] = {}
        self._http_client: Optional[httpx.AsyncClient] = None
        self._fetch_lock = asyncio.Lock()
        # Rate limiting state
        self._last_request_time: float = 0
        self._request_count_minute: int = 0
        self._minute_start: float = 0
        self._rate_limit_lock = asyncio.Lock()
        self._is_rate_limited = False
        self._rate_limit_reset_time: Optional[float] = None
        self.stats = {
            "api_calls": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0,
            "rate_limited": 0,
            "retries": 0,
            "last_fetch": None,
        }

    def _get_cache_key(self, lat: float, lng: float) -> str:
        """Generate cache key from coordinates (rounded to ~10km grid)"""
        # Round to 1 decimal place (~10km resolution) for cache efficiency
        return f"{round(lat, 1)},{round(lng, 1)}"

    def _is_cache_valid(self, cached_time: datetime) -> bool:
        """Check if cached data is still valid"""
        return datetime.now() - cached_time < timedelta(minutes=self.CACHE_TTL_MINUTES)

    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=10.0)

    async def _wait_for_rate_limit(self):
        """Wait if we're being rate limited or need to respect request intervals."""
        async with self._rate_limit_lock:
            now = time.time()

            # Check if we're in a rate-limited cooldown period
            if self._is_rate_limited and self._rate_limit_reset_time:
                wait_time = self._rate_limit_reset_time - now
                if wait_time > 0:
                    print(f"🌤️ Rate limited, waiting {wait_time:.1f}s before next request")
                    await asyncio.sleep(wait_time)
                    now = time.time()
                self._is_rate_limited = False
                self._rate_limit_reset_time = None

            # Reset minute counter if needed
            if now - self._minute_start >= 60:
                self._minute_start = now
                self._request_count_minute = 0

            # Check if we've hit the per-minute limit
            if self._request_count_minute >= self.MAX_REQUESTS_PER_MINUTE:
                wait_time = 60 - (now - self._minute_start)
                if wait_time > 0:
                    print(f"🌤️ Hit per-minute limit ({self.MAX_REQUESTS_PER_MINUTE}), waiting {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
                    self._minute_start = time.time()
                    self._request_count_minute = 0

            # Ensure minimum interval between requests
            time_since_last = now - self._last_request_time
            if time_since_last < self.MIN_REQUEST_INTERVAL:
                await asyncio.sleep(self.MIN_REQUEST_INTERVAL - time_since_last)

            self._last_request_time = time.time()
            self._request_count_minute += 1

    def _handle_rate_limit_error(self, retry_after: Optional[int] = None):
        """Handle a 429 rate limit error by setting cooldown."""
        self._is_rate_limited = True
        # Use retry-after header if provided, otherwise use backoff
        cooldown = retry_after if retry_after else self.BACKOFF_BASE * 2
        self._rate_limit_reset_time = time.time() + cooldown
        self.stats["rate_limited"] += 1
        print(f"🌤️ Rate limit hit, will wait {cooldown}s before retrying")

    async def fetch_weather(self, latitude: float, longitude: float) -> Optional[WeatherConditions]:
        """
        Fetch current weather for a location.

        Uses caching to minimize API calls. Weather is cached at ~10km grid resolution.
        Includes rate limiting and exponential backoff for 429 errors.
        """
        cache_key = self._get_cache_key(latitude, longitude)

        # Check cache first
        if cache_key in self._cache:
            conditions, cached_time = self._cache[cache_key]
            if self._is_cache_valid(cached_time):
                self.stats["cache_hits"] += 1
                return conditions

        self.stats["cache_misses"] += 1

        # Fetch from API with retry logic
        async with self._fetch_lock:
            # Double-check cache after acquiring lock
            if cache_key in self._cache:
                conditions, cached_time = self._cache[cache_key]
                if self._is_cache_valid(cached_time):
                    return conditions

            for attempt in range(self.MAX_RETRIES):
                try:
                    await self._ensure_client()

                    # Wait for rate limit before making request
                    await self._wait_for_rate_limit()

                    params = {
                        "latitude": latitude,
                        "longitude": longitude,
                        "current": [
                            "temperature_2m",
                            "relative_humidity_2m",
                            "precipitation",
                            "weather_code",
                            "cloud_cover",
                            "wind_speed_10m",
                            "wind_gusts_10m",
                            "is_day"
                        ],
                        "timezone": "auto"
                    }

                    response = await self._http_client.get(self.API_URL, params=params)

                    # Handle rate limiting (429 Too Many Requests)
                    if response.status_code == 429:
                        retry_after = response.headers.get("Retry-After")
                        retry_seconds = int(retry_after) if retry_after and retry_after.isdigit() else None
                        self._handle_rate_limit_error(retry_seconds)
                        self.stats["retries"] += 1

                        if attempt < self.MAX_RETRIES - 1:
                            # Exponential backoff: 5s, 10s, 20s
                            backoff = self.BACKOFF_BASE * (2 ** attempt)
                            print(f"🌤️ 429 error, retry {attempt + 1}/{self.MAX_RETRIES} after {backoff}s")
                            await asyncio.sleep(backoff)
                            continue
                        else:
                            # Max retries reached, return None
                            print(f"🌤️ Max retries reached for ({latitude}, {longitude}), skipping")
                            return None

                    response.raise_for_status()
                    data = response.json()

                    self.stats["api_calls"] += 1
                    self.stats["last_fetch"] = datetime.now().isoformat()

                    current = data.get("current", {})

                    conditions = WeatherConditions(
                        latitude=latitude,
                        longitude=longitude,
                        temperature_c=current.get("temperature_2m", 20.0),
                        humidity_percent=current.get("relative_humidity_2m", 50.0),
                        precipitation_mm=current.get("precipitation", 0.0),
                        wind_speed_kmh=current.get("wind_speed_10m", 0.0),
                        wind_gusts_kmh=current.get("wind_gusts_10m", 0.0),
                        cloud_cover_percent=current.get("cloud_cover", 0.0),
                        weather_code=current.get("weather_code", 0),
                        is_day=current.get("is_day", 1) == 1,
                    )

                    # Update cache
                    self._cache[cache_key] = (conditions, datetime.now())

                    # Evict old entries if cache is too large
                    if len(self._cache) > self.MAX_CACHE_SIZE:
                        self._evict_oldest_entries(self.MAX_CACHE_SIZE // 2)

                    return conditions

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        # Already handled above, but catch here for safety
                        continue
                    self.stats["errors"] += 1
                    print(f"Weather API HTTP error for ({latitude}, {longitude}): {e}")
                    return None
                except Exception as e:
                    self.stats["errors"] += 1
                    print(f"Weather API error for ({latitude}, {longitude}): {e}")
                    return None

            return None

    def _evict_oldest_entries(self, keep_count: int):
        """Remove oldest cache entries"""
        if len(self._cache) <= keep_count:
            return

        # Sort by timestamp and keep newest
        sorted_items = sorted(
            self._cache.items(),
            key=lambda x: x[1][1],  # Sort by cached_time
            reverse=True
        )
        self._cache = dict(sorted_items[:keep_count])

    async def fetch_weather_batch(
        self,
        locations: List[Tuple[float, float]]
    ) -> Dict[str, Optional[WeatherConditions]]:
        """
        Fetch weather for multiple locations efficiently.

        Groups nearby locations to reduce API calls.
        """
        results = {}

        # Deduplicate by cache key
        unique_locations = {}
        for lat, lng in locations:
            cache_key = self._get_cache_key(lat, lng)
            if cache_key not in unique_locations:
                unique_locations[cache_key] = (lat, lng)

        # Fetch weather for unique locations (with rate limiting)
        tasks = []
        for cache_key, (lat, lng) in unique_locations.items():
            tasks.append(self.fetch_weather(lat, lng))

        # Limit concurrent requests
        batch_size = 10
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i+batch_size]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)

            for j, result in enumerate(batch_results):
                idx = i + j
                cache_key = list(unique_locations.keys())[idx]
                if isinstance(result, Exception):
                    results[cache_key] = None
                else:
                    results[cache_key] = result

            # Small delay between batches to be nice to the API
            if i + batch_size < len(tasks):
                await asyncio.sleep(0.5)

        return results

    def get_cached_weather(self, latitude: float, longitude: float) -> Optional[WeatherConditions]:
        """Get weather from cache only (no API call). Returns None if not cached."""
        cache_key = self._get_cache_key(latitude, longitude)
        if cache_key in self._cache:
            conditions, cached_time = self._cache[cache_key]
            if self._is_cache_valid(cached_time):
                return conditions
        return None

    def get_stats(self) -> dict:
        """Get service statistics"""
        return {
            **self.stats,
            "cache_size": len(self._cache),
            "cache_ttl_minutes": self.CACHE_TTL_MINUTES,
        }

    async def close(self):
        """Close HTTP client"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Singleton instance
weather_service = WeatherService()


def apply_weather_to_kpi(
    kpi_data: dict,
    weather: Optional[WeatherConditions]
) -> dict:
    """
    Apply weather effects to KPI metrics.

    This function modifies KPI values based on current weather conditions
    to simulate realistic cable plant (HFC) network behavior.
    """
    if weather is None:
        return kpi_data

    # Get impact factors
    rain = weather.rain_impact
    temp = weather.temperature_impact
    wind = weather.wind_impact
    overall = weather.overall_impact

    # Apply weather effects to cable plant KPIs
    # Rain: RF signal degradation, moisture ingress into connectors
    if rain > 0:
        kpi_data["ds_power_level_dbmv"] = kpi_data.get("ds_power_level_dbmv", 0) - (rain * 3)  # Up to -3 dBmV
        kpi_data["us_power_level_dbmv"] = kpi_data.get("us_power_level_dbmv", 40) + (rain * 3)  # Modems compensate
        kpi_data["ds_snr_db"] = kpi_data.get("ds_snr_db", 38) - (rain * 5)  # Up to -5 dB SNR loss
        kpi_data["us_snr_db"] = kpi_data.get("us_snr_db", 30) - (rain * 4)  # Up to -4 dB
        kpi_data["packet_loss_percent"] = min(10, kpi_data.get("packet_loss_percent", 0.5) + (rain * 3))
        kpi_data["downstream_throughput_mbps"] = max(10, kpi_data.get("downstream_throughput_mbps", 500) * (1 - rain * 0.3))
        kpi_data["fec_uncorrected_codewords"] = int(kpi_data.get("fec_uncorrected_codewords", 0) + (rain * 50))

    # Temperature effects on node/amplifier equipment
    if temp > 0:
        kpi_data["node_cpu_utilization"] = min(100, kpi_data.get("node_cpu_utilization", 45) + (temp * 25))
        kpi_data["node_temperature"] = kpi_data.get("node_temperature", 40) + (temp * 20)
        # Thermal throttling reduces throughput and increases modem flaps
        if kpi_data.get("node_temperature", 40) > 70:
            kpi_data["downstream_throughput_mbps"] = kpi_data.get("downstream_throughput_mbps", 500) * 0.8
            kpi_data["modems_with_flaps"] = int(kpi_data.get("modems_with_flaps", 2) + (temp * 10))

    # Wind effects on aerial cable plant
    if wind > 0:
        kpi_data["ds_snr_db"] = max(20, kpi_data.get("ds_snr_db", 38) - (wind * 3))  # Cable sway degrades signal
        kpi_data["t3_timeouts"] = int(kpi_data.get("t3_timeouts", 0) + (wind * 5))
        kpi_data["modems_with_flaps"] = int(kpi_data.get("modems_with_flaps", 2) + (wind * 8))
        kpi_data["offline_modems"] = int(kpi_data.get("offline_modems", 5) + (wind * 3))

    # Overall weather impact on network performance
    if overall > 0:
        kpi_data["latency_ms"] = kpi_data.get("latency_ms", 15) * (1 + overall * 0.5)
        kpi_data["jitter_ms"] = kpi_data.get("jitter_ms", 3) * (1 + overall * 0.8)
        kpi_data["t4_timeouts"] = int(kpi_data.get("t4_timeouts", 0) + (overall * 3))

    # Add weather metadata to KPI
    kpi_data["weather_conditions"] = weather.get_weather_description()
    kpi_data["weather_impact"] = round(overall, 3)
    kpi_data["temperature_outdoor"] = weather.temperature_c
    kpi_data["precipitation_mm"] = weather.precipitation_mm
    kpi_data["wind_speed_kmh"] = weather.wind_speed_kmh

    return kpi_data
