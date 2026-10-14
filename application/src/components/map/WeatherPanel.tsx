import { useEffect, useState, useMemo } from 'react';
import {
  Cloud,
  CloudRain,
  CloudSnow,
  Sun,
  CloudLightning,
  Wind,
  Thermometer,
  AlertTriangle
} from 'lucide-react';

interface WeatherRegion {
  region: string;
  node_count: number;
  conditions: Record<string, number>;
  avg_temperature: number | null;
  avg_wind_speed: number | null;
  avg_precipitation: number | null;
  avg_weather_impact: number;
  nodes_with_impact: number;
}

interface WeatherSummary {
  timestamp: string;
  total_nodes_with_weather: number;
  nodes_with_significant_impact: number;
  weather_conditions_summary: Record<string, number>;
  regions: WeatherRegion[];
  extreme_weather_nodes: string[];
  avg_global_impact: number;
}

interface WeatherPanelProps {
  apiBaseUrl?: string;
  refreshInterval?: number;
}

const getWeatherIcon = (condition: string, size: number = 16) => {
  const lowerCondition = condition.toLowerCase();

  if (lowerCondition.includes('thunder') || lowerCondition.includes('storm')) {
    return <CloudLightning size={size} className="text-yellow-400" />;
  }
  if (lowerCondition.includes('snow')) {
    return <CloudSnow size={size} className="text-blue-300" />;
  }
  if (lowerCondition.includes('rain') || lowerCondition.includes('drizzle')) {
    return <CloudRain size={size} className="text-blue-400" />;
  }
  if (lowerCondition.includes('clear')) {
    return <Sun size={size} className="text-yellow-300" />;
  }
  if (lowerCondition.includes('fog')) {
    return <Cloud size={size} className="text-gray-400" />;
  }
  return <Cloud size={size} className="text-gray-300" />;
};

const getImpactColor = (impact: number): string => {
  if (impact >= 0.5) return 'text-red-500';
  if (impact >= 0.3) return 'text-orange-500';
  if (impact >= 0.1) return 'text-yellow-500';
  return 'text-green-500';
};

const WeatherPanel = ({ apiBaseUrl = '', refreshInterval = 60000 }: WeatherPanelProps) => {
  const [weather, setWeather] = useState<WeatherSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const fetchWeather = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/api/v1/weather/summary`);
        if (!response.ok) throw new Error('Failed to fetch weather');
        const data = await response.json();
        setWeather(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchWeather();
    const interval = setInterval(fetchWeather, refreshInterval);
    return () => clearInterval(interval);
  }, [apiBaseUrl, refreshInterval]);

  // Get top weather conditions
  const topConditions = useMemo(() => {
    if (!weather) return [];
    return Object.entries(weather.weather_conditions_summary)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
  }, [weather]);

  // Get regions with weather impact
  const impactedRegions = useMemo(() => {
    if (!weather) return [];
    return weather.regions
      .filter(r => r.nodes_with_impact > 0)
      .sort((a, b) => b.avg_weather_impact - a.avg_weather_impact)
      .slice(0, 5);
  }, [weather]);

  if (loading) {
    return (
      <div className="absolute top-16 left-4 bg-gray-800 rounded-lg shadow-lg border border-gray-700 p-3 z-[1000]">
        <div className="flex items-center gap-2 text-gray-400 text-sm">
          <Cloud className="w-4 h-4 animate-pulse" />
          Loading weather...
        </div>
      </div>
    );
  }

  if (error || !weather) {
    return (
      <div className="absolute top-16 left-4 bg-gray-800 rounded-lg shadow-lg border border-gray-700 p-3 z-[1000]">
        <div className="flex items-center gap-2 text-gray-500 text-sm">
          <Cloud className="w-4 h-4" />
          Weather unavailable
        </div>
      </div>
    );
  }

  const hasExtremeWeather = weather.extreme_weather_nodes.length > 0;
  const hasSignificantImpact = weather.nodes_with_significant_impact > 0;

  return (
    <div
      className={`absolute top-16 left-4 bg-gray-800 rounded-lg shadow-lg border border-gray-700 z-[1000] transition-all duration-200 ${
        expanded ? 'w-80' : 'w-auto'
      }`}
    >
      {/* Compact Header - Always Visible */}
      <div
        className="p-3 cursor-pointer hover:bg-gray-750"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          {/* Weather Icon & Count */}
          <div className="flex items-center gap-2">
            {hasExtremeWeather ? (
              <AlertTriangle className="w-5 h-5 text-orange-500 animate-pulse" />
            ) : (
              <Cloud className="w-5 h-5 text-blue-400" />
            )}
            <div>
              <div className="text-sm font-medium text-white">
                {weather.total_nodes_with_weather.toLocaleString()} nodes
              </div>
              <div className="text-xs text-gray-400">with weather data</div>
            </div>
          </div>

          {/* Impact Badge */}
          {hasSignificantImpact && (
            <div className="bg-orange-500/20 text-orange-400 text-xs px-2 py-0.5 rounded-full">
              {weather.nodes_with_significant_impact} impacted
            </div>
          )}

          {/* Global Impact */}
          <div className={`text-sm font-medium ${getImpactColor(weather.avg_global_impact)}`}>
            {(weather.avg_global_impact * 100).toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      {expanded && (
        <div className="border-t border-gray-700 p-3 space-y-4">
          {/* Weather Conditions */}
          <div>
            <div className="text-xs text-gray-400 mb-2 flex items-center gap-1">
              <Cloud className="w-3 h-3" /> Conditions
            </div>
            <div className="flex flex-wrap gap-2">
              {topConditions.map(([condition, count]) => (
                <div
                  key={condition}
                  className="flex items-center gap-1 bg-gray-700 rounded px-2 py-1"
                >
                  {getWeatherIcon(condition, 12)}
                  <span className="text-xs text-gray-300">{condition}</span>
                  <span className="text-xs text-gray-500">({count})</span>
                </div>
              ))}
            </div>
          </div>

          {/* Impacted Regions */}
          {impactedRegions.length > 0 && (
            <div>
              <div className="text-xs text-gray-400 mb-2 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" /> Weather Impact by Region
              </div>
              <div className="space-y-1">
                {impactedRegions.map(region => (
                  <div
                    key={region.region}
                    className="flex items-center justify-between text-xs bg-gray-700/50 rounded px-2 py-1"
                  >
                    <span className="text-gray-300">{region.region}</span>
                    <div className="flex items-center gap-2">
                      {region.avg_temperature !== null && (
                        <span className="text-gray-400 flex items-center gap-0.5">
                          <Thermometer className="w-3 h-3" />
                          {region.avg_temperature.toFixed(0)}°
                        </span>
                      )}
                      {region.avg_wind_speed !== null && region.avg_wind_speed > 10 && (
                        <span className="text-gray-400 flex items-center gap-0.5">
                          <Wind className="w-3 h-3" />
                          {region.avg_wind_speed.toFixed(0)}
                        </span>
                      )}
                      <span className={getImpactColor(region.avg_weather_impact)}>
                        {(region.avg_weather_impact * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Extreme Weather Alert */}
          {hasExtremeWeather && (
            <div className="bg-red-500/10 border border-red-500/30 rounded p-2">
              <div className="flex items-center gap-2 text-red-400 text-xs font-medium mb-1">
                <AlertTriangle className="w-3 h-3" />
                Extreme Weather ({weather.extreme_weather_nodes.length} nodes)
              </div>
              <div className="text-xs text-gray-400">
                {weather.extreme_weather_nodes.slice(0, 5).join(', ')}
                {weather.extreme_weather_nodes.length > 5 && '...'}
              </div>
            </div>
          )}

          {/* Last Updated */}
          <div className="text-xs text-gray-500 text-right">
            Updated: {new Date(weather.timestamp).toLocaleTimeString()}
          </div>
        </div>
      )}
    </div>
  );
};

export default WeatherPanel;
