import { memo, useState, useEffect, useCallback, useMemo } from 'react';
import { FiberNode, NetworkHealthSummary, Region, GeographicRegion } from '@/types';
import { SERVICE_AREA_TO_REGION } from '@/constants';
import GlobalMap from '../map/GlobalMap';
import type { MapLayerVisibility } from '../map/GlobalMap';
import MapLayerControl from '../map/MapLayerControl';
import MapLegend from '../map/MapLegend';
import MapStats, { NodeStatusFilter } from '../map/MapStats';
import WeatherPanel from '../map/WeatherPanel';
import NetworkHealthPanel from '../panels/NetworkHealthPanel';
import HorizontalKPIPanel, { FilterType } from '../panels/HorizontalKPIPanel';
import NodeStatusReportModal from '../panels/NodeStatusReportModal';
import HeadendDetailModal from '../map/HeadendDetailModal';
import HubDetailModal from '../map/HubDetailModal';
import GeographicFilterPanel, { GeographicFilterState } from '../panels/GeographicFilterPanel';
import {
  getNetworkHealthSummary,
  getRecentKPIMetrics,
} from '@/services/memoryStore';
import { getHeadends, getHubs } from '@/services/api';
import type { Headend, Hub } from '@/services/api';
import { aggregateKPITrends, AggregatedKPITrends, KPICurrentValues } from '@/services/kpiAggregator';
import { UPDATE_INTERVALS } from '@/constants';

interface MapDashboardProps {
  nodes: FiberNode[];
  onProviderChange?: (provider: string | null) => void;
}

const MapDashboard = memo(({ nodes, onProviderChange }: MapDashboardProps) => {
  const [healthSummary, setHealthSummary] = useState<NetworkHealthSummary | null>(null);
  const [kpiTrends, setKpiTrends] = useState<AggregatedKPITrends | null>(null);
  const [kpiCurrent, setKpiCurrent] = useState<KPICurrentValues | null>(null);
  const [regionFilter, setRegionFilter] = useState<FilterType>('all');
  const [nodeStatusFilter, setNodeStatusFilter] = useState<NodeStatusFilter>('all');
  const [geoFilter, setGeoFilter] = useState<GeographicFilterState>({
    selectedRegions: [],
    selectedProviders: [],
  });
  const [showAIReport, setShowAIReport] = useState(false);
  const [aiReportNode, setAiReportNode] = useState<FiberNode | null>(null);

  // Infrastructure state
  const [headends, setHeadends] = useState<Headend[]>([]);
  const [hubs, setHubs] = useState<Hub[]>([]);
  const [layerVisibility, setLayerVisibility] = useState<MapLayerVisibility>({
    headends: true,
    hubs: true,
    nodes: true,
    customerDensity: false,
  });
  const [selectedHeadend, setSelectedHeadend] = useState<Headend | null>(null);
  const [selectedHub, setSelectedHub] = useState<Hub | null>(null);

  // Fetch infrastructure data once on mount (static data, no polling needed)
  useEffect(() => {
    const fetchInfrastructure = async () => {
      try {
        const [headendRes, hubRes] = await Promise.all([
          getHeadends(),
          getHubs(),
        ]);
        setHeadends(headendRes.headends);
        setHubs(hubRes.hubs);
      } catch (err) {
        console.error('[MapDashboard] Failed to fetch infrastructure:', err);
      }
    };
    fetchInfrastructure();
  }, []);

  // Memoized geographic filter handler
  const handleGeoFilterChange = useCallback((filter: GeographicFilterState) => {
    setGeoFilter(filter);
    // Notify parent of provider change for header title
    if (onProviderChange) {
      if (filter.selectedProviders.length === 1) {
        onProviderChange(filter.selectedProviders[0]);
      } else {
        onProviderChange(null);
      }
    }
  }, [onProviderChange]);

  // Filter nodes based on geographic filter and status filter
  const filteredNodes = useMemo(() => {
    return nodes.filter(node => {
      // Apply geographic region filter (map service area name to US region)
      const nodeRegion = SERVICE_AREA_TO_REGION[node.region] || node.region;
      const matchesRegion = geoFilter.selectedRegions.length === 0 ||
        geoFilter.selectedRegions.includes(nodeRegion as GeographicRegion);

      // Apply provider filter
      const matchesProvider = geoFilter.selectedProviders.length === 0 ||
        (node.manufacturer ? geoFilter.selectedProviders.includes(node.manufacturer) : false);

      return matchesRegion && matchesProvider;
    });
  }, [nodes, geoFilter]);

  // Note: Backend refresh is now handled by the parent Dashboard component.
  // This component only reads from the local store.

  // Refresh dashboard UI from local store periodically (matches UI_REFRESH interval - 5 seconds)
  useEffect(() => {
    const refreshData = async () => {
      const [summary, kpiMetrics] = await Promise.all([
        getNetworkHealthSummary(),
        getRecentKPIMetrics(2000), // 2k records sufficient for 5-second trend buckets
      ]);

      setHealthSummary(summary);

      // Aggregate KPI trends from recent data
      const { trends, current } = aggregateKPITrends(
        kpiMetrics,
        5000, // 5 second buckets
        nodes, // Pass nodes for region filtering
        regionFilter === 'all' ? 'all' : regionFilter as Region
      );
      setKpiTrends(trends);
      setKpiCurrent(current);
    };

    refreshData();
    const interval = setInterval(refreshData, UPDATE_INTERVALS.UI_REFRESH);

    return () => clearInterval(interval);
  }, [regionFilter, nodes]);

  const handleNodeClick = async (node: FiberNode) => {
    // Show AI-powered node analysis report
    setAiReportNode(node);
    setShowAIReport(true);
  };

  const handleCloseAIReport = () => {
    setShowAIReport(false);
    setAiReportNode(null);
  };

  const handleHeadendClick = useCallback((headend: Headend) => {
    setSelectedHeadend(headend);
  }, []);

  const handleHubClick = useCallback((hub: Hub) => {
    setSelectedHub(hub);
  }, []);

  return (
    <div className="space-y-6">
      {/* Network Health Summary */}
      {healthSummary && <NetworkHealthPanel summary={healthSummary} />}

      {/* Geographic Filter Panel */}
      <GeographicFilterPanel
        nodes={nodes}
        onFilterChange={handleGeoFilterChange}
      />

      {/* Map - Full Width */}
      <div className="bg-gray-800 rounded-lg shadow-lg border border-gray-700 overflow-hidden relative">
        <div className="h-[600px]">
          <GlobalMap
            nodes={filteredNodes}
            onNodeClick={handleNodeClick}
            statusFilter={nodeStatusFilter}
            headends={headends}
            hubs={hubs}
            layerVisibility={layerVisibility}
            onHeadendClick={handleHeadendClick}
            onHubClick={handleHubClick}
          />
          <MapLayerControl
            layerVisibility={layerVisibility}
            onVisibilityChange={setLayerVisibility}
            headendCount={headends.length}
            hubCount={hubs.length}
            nodeCount={filteredNodes.length}
          />
          <WeatherPanel refreshInterval={60000} />
          <MapStats
            nodes={filteredNodes}
            statusFilter={nodeStatusFilter}
            onFilterChange={setNodeStatusFilter}
            headendCount={headends.length}
            hubCount={hubs.length}
          />
          <MapLegend nodes={filteredNodes} headendCount={headends.length} hubCount={hubs.length} />
        </div>
      </div>

      {/* KPI Trends - Horizontal Below Map */}
      {kpiTrends && kpiCurrent ? (
        <HorizontalKPIPanel
          trends={kpiTrends}
          current={kpiCurrent}
          onFilterChange={(filter) => setRegionFilter(filter)}
        />
      ) : (
        <div className="bg-gray-800 rounded-lg shadow-lg border border-gray-700 p-6 h-full flex items-center justify-center">
          <p className="text-gray-400">Loading KPI trends...</p>
        </div>
      )}

      {/* AI Node Status Report Modal */}
      {showAIReport && aiReportNode && (
        <NodeStatusReportModal
          key={aiReportNode.node_id}
          node={aiReportNode}
          onClose={handleCloseAIReport}
        />
      )}

      {/* Headend Detail Modal */}
      {selectedHeadend && (
        <HeadendDetailModal
          headend={selectedHeadend}
          onClose={() => setSelectedHeadend(null)}
        />
      )}

      {/* Hub Detail Modal */}
      {selectedHub && (
        <HubDetailModal
          hub={selectedHub}
          onClose={() => setSelectedHub(null)}
        />
      )}
    </div>
  );
});

MapDashboard.displayName = 'MapDashboard';

export default MapDashboard;
