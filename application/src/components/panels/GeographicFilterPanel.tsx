import { memo, useState, useEffect } from 'react';
import { Globe, Building2, ChevronDown, X, Filter } from 'lucide-react';
import { GeographicRegion, FiberNode } from '@/types';
import { PROVIDERS_BY_REGION, PROVIDER_COLORS, SERVICE_AREA_TO_REGION } from '@/constants';

export interface GeographicFilterState {
  selectedRegions: GeographicRegion[];
  selectedProviders: string[];
}

interface GeographicFilterPanelProps {
  nodes: FiberNode[];
  onFilterChange: (filter: GeographicFilterState) => void;
}

const REGION_LABELS: Record<GeographicRegion, string> = {
  [GeographicRegion.NORTHEAST]: 'Northeast US',
  [GeographicRegion.SOUTHEAST]: 'Southeast US',
  [GeographicRegion.MIDWEST]: 'Midwest US',
  [GeographicRegion.SOUTH_CENTRAL]: 'South Central US',
  [GeographicRegion.MOUNTAIN]: 'Mountain US',
  [GeographicRegion.PACIFIC]: 'Pacific US',
  [GeographicRegion.CANADA]: 'Canada',
  [GeographicRegion.LATIN_AMERICA]: 'Latin America',
  [GeographicRegion.EUROPE]: 'Europe',
  [GeographicRegion.MIDDLE_EAST]: 'Middle East',
  [GeographicRegion.APAC]: 'Asia Pacific',
  [GeographicRegion.OCEANIA]: 'Oceania',
  [GeographicRegion.AFRICA]: 'Africa',
};

const GeographicFilterPanel = memo(({ nodes, onFilterChange }: GeographicFilterPanelProps) => {
  const [selectedRegions, setSelectedRegions] = useState<GeographicRegion[]>([]);
  const [selectedProviders, setSelectedProviders] = useState<string[]>([]);
  const [showRegionDropdown, setShowRegionDropdown] = useState(false);
  const [showProviderDropdown, setShowProviderDropdown] = useState(false);

  // Get available providers based on selected regions
  const availableProviders = selectedRegions.length > 0
    ? selectedRegions.flatMap(region => PROVIDERS_BY_REGION[region] || [])
    : Object.values(PROVIDERS_BY_REGION).flat();

  // Get counts for display
  const getNodeCountByRegion = (region: GeographicRegion): number => {
    return nodes.filter(t => (SERVICE_AREA_TO_REGION[t.region] || t.region) === region).length;
  };

  const getNodeCountByProvider = (provider: string): number => {
    return nodes.filter(t => t.manufacturer === provider).length;
  };

  // Notify parent of filter changes
  useEffect(() => {
    onFilterChange({ selectedRegions, selectedProviders });
  }, [selectedRegions, selectedProviders, onFilterChange]);

  const handleRegionToggle = (region: GeographicRegion) => {
    setSelectedRegions(prev => {
      if (prev.includes(region)) {
        // Removing region - also remove providers from that region
        const regionProviders = PROVIDERS_BY_REGION[region] || [];
        setSelectedProviders(current =>
          current.filter(p => !regionProviders.includes(p))
        );
        return prev.filter(r => r !== region);
      } else {
        return [...prev, region];
      }
    });
  };

  const handleProviderToggle = (provider: string) => {
    setSelectedProviders(prev =>
      prev.includes(provider)
        ? prev.filter(p => p !== provider)
        : [...prev, provider]
    );
  };

  const clearAllFilters = () => {
    setSelectedRegions([]);
    setSelectedProviders([]);
  };

  const hasActiveFilters = selectedRegions.length > 0 || selectedProviders.length > 0;

  // Calculate filtered node count
  const filteredCount = nodes.filter(t => {
    const matchesRegion = selectedRegions.length === 0 || selectedRegions.includes((SERVICE_AREA_TO_REGION[t.region] || t.region) as GeographicRegion);
    const matchesProvider = selectedProviders.length === 0 || (t.manufacturer ? selectedProviders.includes(t.manufacturer) : false);
    return matchesRegion && matchesProvider;
  }).length;

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4 relative z-[1000]">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-blue-400" />
          <h3 className="text-sm font-medium text-white">Geographic Filter</h3>
        </div>
        {hasActiveFilters && (
          <button
            onClick={clearAllFilters}
            className="text-xs text-gray-400 hover:text-white flex items-center gap-1"
          >
            <X className="w-3 h-3" />
            Clear all
          </button>
        )}
      </div>

      <div className="flex flex-wrap gap-3">
        {/* Region Selector */}
        <div className="relative">
          <button
            onClick={() => {
              setShowRegionDropdown(!showRegionDropdown);
              setShowProviderDropdown(false);
            }}
            className="flex items-center gap-2 px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm text-white transition-colors"
          >
            <Globe className="w-4 h-4 text-blue-400" />
            <span>
              {selectedRegions.length === 0
                ? 'All Regions'
                : `${selectedRegions.length} Region${selectedRegions.length > 1 ? 's' : ''}`}
            </span>
            <ChevronDown className={`w-4 h-4 transition-transform ${showRegionDropdown ? 'rotate-180' : ''}`} />
          </button>

          {showRegionDropdown && (
            <div className="absolute top-full left-0 mt-1 w-56 bg-gray-700 rounded-lg shadow-lg border border-gray-600 z-[1100] max-h-80 overflow-y-auto">
              {Object.values(GeographicRegion).map(region => {
                const count = getNodeCountByRegion(region);
                const isSelected = selectedRegions.includes(region);
                return (
                  <button
                    key={region}
                    onClick={() => handleRegionToggle(region)}
                    className={`w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-gray-600 transition-colors ${
                      isSelected ? 'bg-blue-600/20 text-blue-400' : 'text-gray-300'
                    }`}
                  >
                    <span>{REGION_LABELS[region]}</span>
                    <span className="text-xs text-gray-500">{count} nodes</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Provider Selector */}
        <div className="relative">
          <button
            onClick={() => {
              setShowProviderDropdown(!showProviderDropdown);
              setShowRegionDropdown(false);
            }}
            className="flex items-center gap-2 px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm text-white transition-colors"
          >
            <Building2 className="w-4 h-4 text-purple-400" />
            <span>
              {selectedProviders.length === 0
                ? 'All Providers'
                : `${selectedProviders.length} Provider${selectedProviders.length > 1 ? 's' : ''}`}
            </span>
            <ChevronDown className={`w-4 h-4 transition-transform ${showProviderDropdown ? 'rotate-180' : ''}`} />
          </button>

          {showProviderDropdown && (
            <div className="absolute top-full left-0 mt-1 w-64 bg-gray-700 rounded-lg shadow-lg border border-gray-600 z-[1100] max-h-80 overflow-y-auto">
              {[...new Set(availableProviders)].map(provider => {
                const count = getNodeCountByProvider(provider);
                const isSelected = selectedProviders.includes(provider);
                const color = PROVIDER_COLORS[provider] || '#888888';
                return (
                  <button
                    key={provider}
                    onClick={() => handleProviderToggle(provider)}
                    className={`w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-gray-600 transition-colors ${
                      isSelected ? 'bg-purple-600/20 text-purple-400' : 'text-gray-300'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: color }}
                      />
                      <span>{provider}</span>
                    </div>
                    <span className="text-xs text-gray-500">{count} nodes</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Selected Chips */}
        <div className="flex flex-wrap gap-2 items-center">
          {selectedRegions.map(region => (
            <span
              key={region}
              className="inline-flex items-center gap-1 px-2 py-1 bg-blue-600/20 text-blue-400 rounded text-xs"
            >
              {REGION_LABELS[region]}
              <button onClick={() => handleRegionToggle(region)} className="hover:text-white">
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
          {selectedProviders.map(provider => (
            <span
              key={provider}
              className="inline-flex items-center gap-1 px-2 py-1 bg-purple-600/20 text-purple-400 rounded text-xs"
            >
              {provider}
              <button onClick={() => handleProviderToggle(provider)} className="hover:text-white">
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>

        {/* Node Count */}
        <div className="ml-auto text-sm text-gray-400">
          Showing <span className="text-white font-medium">{filteredCount}</span> of {nodes.length} nodes
        </div>
      </div>

      {/* Click outside to close dropdowns */}
      {(showRegionDropdown || showProviderDropdown) && (
        <div
          className="fixed inset-0 z-[1050]"
          onClick={() => {
            setShowRegionDropdown(false);
            setShowProviderDropdown(false);
          }}
        />
      )}
    </div>
  );
});

GeographicFilterPanel.displayName = 'GeographicFilterPanel';

export default GeographicFilterPanel;
