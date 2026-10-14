import { useEffect, useRef, memo } from 'react';
import L from 'leaflet';
import { basemapTileUrl, BASEMAP_ATTRIBUTION, resolveCartoApiKey } from '../../config/basemap';
import { BASEMAP_SETTINGS_CHANGED_EVENT } from '../../services/systemSettingsService';
import { FiberNode, NodeStatus } from '@/types';
import { getMarkerColor } from '@/utils/helpers';
import { NodeStatusFilter } from './MapStats';
import type { Headend, Hub } from '@/services/api/coreNetworkApi';

export interface MapLayerVisibility {
  headends: boolean;
  hubs: boolean;
  nodes: boolean;
  customerDensity: boolean;
}

interface GlobalMapProps {
  nodes: FiberNode[];
  onNodeClick: (node: FiberNode) => void;
  statusFilter?: NodeStatusFilter;
  headends?: Headend[];
  hubs?: Hub[];
  layerVisibility?: MapLayerVisibility;
  onHeadendClick?: (headend: Headend) => void;
  onHubClick?: (hub: Hub) => void;
}

const STATUS_COLORS: Record<string, string> = {
  operational: '#10b981',
  degraded: '#f59e0b',
  failed: '#ef4444',
  maintenance: '#6b7280',
  unknown: '#6b7280',
};

function getInfraColor(status: string): string {
  return STATUS_COLORS[status.toLowerCase()] || STATUS_COLORS.unknown;
}

const GlobalMap = memo(({
  nodes,
  onNodeClick,
  statusFilter = 'all',
  headends = [],
  hubs = [],
  layerVisibility = { headends: true, hubs: true, nodes: true, customerDensity: false },
  onHeadendClick,
  onHubClick,
}: GlobalMapProps) => {
  const mapRef = useRef<L.Map | null>(null);
  const markersRef = useRef<Map<string, L.CircleMarker>>(new Map());
  // Track previous node status to only update changed markers
  const prevNodeStatusRef = useRef<Map<string, string>>(new Map());
  const prevStatusFilterRef = useRef<NodeStatusFilter>('all');
  // Track hidden markers for cleanup
  const hiddenMarkersTimeRef = useRef<Map<string, number>>(new Map());

  // Layer groups for infrastructure
  const headendLayerRef = useRef<L.LayerGroup | null>(null);
  const hubLayerRef = useRef<L.LayerGroup | null>(null);
  const nodeLayerRef = useRef<L.LayerGroup | null>(null);
  const densityLayerRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    // Initialize map only once
    if (!mapRef.current) {
      const mapContainer = document.getElementById('map');
      if (!mapContainer) {
        console.error('Map container not found!');
        return;
      }

      // Clear any existing Leaflet instances
      mapContainer.innerHTML = '';
      mapContainer.className = 'w-full h-full';

      const map = L.map('map', {
        center: [20, 0],
        zoom: 2,
        minZoom: 2,
        maxZoom: 18,
        maxBounds: [
          [-90, -180],
          [90, 180],
        ],
        maxBoundsViscosity: 1.0,
        preferCanvas: false,
        zoomControl: false,
      });

      // Add zoom control to bottom-left
      L.control.zoom({
        position: 'bottomleft'
      }).addTo(map);

      // CARTO basemap; URL/key/style come from VITE_CARTO_* env vars (see src/config/basemap.ts)
      const tiles = L.tileLayer(basemapTileUrl(), {
        attribution: BASEMAP_ATTRIBUTION,
        subdomains: 'abcd',
        maxZoom: 20,
        crossOrigin: 'anonymous',
      }).addTo(map);
      let tileErrorLogged = false;
      tiles.on('tileerror', () => {
        if (tileErrorLogged) return;
        tileErrorLogged = true;
        console.warn(
          resolveCartoApiKey()
            ? 'Basemap tiles failed to load; check the CARTO API key in Settings -> Map Basemap.'
            : 'Basemap tiles failed to load; add a CARTO API key in Settings -> Map Basemap if your account requires authentication.'
        );
      });
      // Re-tile when the CARTO key/style is saved from the settings panel
      const onBasemapChange = () => {
        tileErrorLogged = false;
        tiles.setUrl(basemapTileUrl());
      };
      window.addEventListener(BASEMAP_SETTINGS_CHANGED_EVENT, onBasemapChange);
      map.once('remove', () => window.removeEventListener(BASEMAP_SETTINGS_CHANGED_EVENT, onBasemapChange));

      // Create custom panes for z-index control
      const densityPane = map.createPane('densityPane');
      densityPane.style.zIndex = '350';
      const nodePane = map.createPane('nodePane');
      nodePane.style.zIndex = '400';
      const hubPane = map.createPane('hubPane');
      hubPane.style.zIndex = '450';
      const headendPane = map.createPane('headendPane');
      headendPane.style.zIndex = '500';

      // Initialize layer groups
      densityLayerRef.current = L.layerGroup().addTo(map);
      nodeLayerRef.current = L.layerGroup().addTo(map);
      hubLayerRef.current = L.layerGroup().addTo(map);
      headendLayerRef.current = L.layerGroup().addTo(map);

      mapRef.current = map;
    }

    return () => {
      // Cleanup on unmount
      if (mapRef.current) {
        markersRef.current.clear();
        headendLayerRef.current = null;
        hubLayerRef.current = null;
        nodeLayerRef.current = null;
        densityLayerRef.current = null;
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  // Keep a ref to the current nodes so click handlers always have the latest data
  const nodesRef = useRef<Map<string, FiberNode>>(new Map());

  // Update nodes ref whenever nodes change
  useEffect(() => {
    nodesRef.current = new Map(nodes.map((t) => [t.node_id, t]));
  }, [nodes]);

  // Manage layer visibility
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const toggleLayer = (layer: L.LayerGroup | null, visible: boolean) => {
      if (!layer) return;
      if (visible && !map.hasLayer(layer)) {
        layer.addTo(map);
      } else if (!visible && map.hasLayer(layer)) {
        map.removeLayer(layer);
      }
    };

    toggleLayer(headendLayerRef.current, layerVisibility.headends);
    toggleLayer(hubLayerRef.current, layerVisibility.hubs);
    toggleLayer(nodeLayerRef.current, layerVisibility.nodes);
    toggleLayer(densityLayerRef.current, layerVisibility.customerDensity);
  }, [layerVisibility]);

  // Render headend markers
  useEffect(() => {
    const layer = headendLayerRef.current;
    if (!layer || !mapRef.current) return;

    layer.clearLayers();
    if (headends.length === 0) return;

    headends.forEach((he) => {
      if (!he.latitude || !he.longitude) return;

      const color = getInfraColor(he.status);
      const icon = L.divIcon({
        className: 'headend-marker',
        html: `<div style="
          width: 22px; height: 22px;
          background: ${color};
          border: 2px solid white;
          border-radius: 3px;
          box-shadow: 0 0 8px ${color}80;
        "></div>`,
        iconSize: [22, 22],
        iconAnchor: [11, 11],
      });

      const marker = L.marker([he.latitude, he.longitude], {
        icon,
        pane: 'headendPane',
      });

      marker.bindTooltip(
        `<div class="text-sm" style="min-width: 160px;">
          <strong>${he.name}</strong><br/>
          <span style="color: ${color}; font-weight: bold;">${he.status.toUpperCase()}</span><br/>
          CMTS: ${he.cmts_count} &bull; Ports: ${he.port_utilization_percent}% used<br/>
          Subscribers: ${(he.total_active_subscribers).toLocaleString()}<br/>
          ${he.city}, ${he.state}
        </div>`,
        { direction: 'top', offset: [0, -14] }
      );

      if (onHeadendClick) {
        marker.on('click', () => onHeadendClick(he));
      }

      marker.addTo(layer);
    });
  }, [headends, onHeadendClick]);

  // Render hub markers
  useEffect(() => {
    const layer = hubLayerRef.current;
    if (!layer || !mapRef.current) return;

    layer.clearLayers();
    if (hubs.length === 0) return;

    hubs.forEach((hub) => {
      if (!hub.latitude || !hub.longitude) return;

      const color = getInfraColor(hub.status);
      const icon = L.divIcon({
        className: 'hub-marker',
        html: `<div style="
          width: 14px; height: 14px;
          background: ${color};
          border: 1.5px solid white;
          border-radius: 2px;
          transform: rotate(45deg);
          box-shadow: 0 0 6px ${color}60;
        "></div>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      });

      const marker = L.marker([hub.latitude, hub.longitude], {
        icon,
        pane: 'hubPane',
      });

      marker.bindTooltip(
        `<div class="text-sm" style="min-width: 140px;">
          <strong>${hub.name}</strong><br/>
          <span style="color: ${color}; font-weight: bold;">${hub.status.toUpperCase()}</span><br/>
          Nodes: ${hub.fiber_nodes_served} &bull; ${hub.utilization_percent}% util.<br/>
          Throughput: ${hub.current_throughput_gbps} / ${hub.fiber_capacity_gbps} Gbps
        </div>`,
        { direction: 'top', offset: [0, -10] }
      );

      if (onHubClick) {
        marker.on('click', () => onHubClick(hub));
      }

      marker.addTo(layer);
    });
  }, [hubs, onHubClick]);

  // Render customer density rings (only on first render or node count change)
  const prevDensityCountRef = useRef<number>(0);
  useEffect(() => {
    const layer = densityLayerRef.current;
    if (!layer || !mapRef.current) return;

    // Only rebuild density layer when node count changes (density is static per node)
    if (nodes.length === prevDensityCountRef.current) return;
    prevDensityCountRef.current = nodes.length;

    layer.clearLayers();
    if (nodes.length === 0) return;

    nodes.forEach((node) => {
      const homesActive = (node as FiberNode & { homes_active?: number }).homes_active || 0;
      if (homesActive === 0) return;

      // Scale radius: 6px min, 20px max based on homes_active
      const minR = 6, maxR = 20;
      const maxHomes = 500; // typical max homes_active
      const radius = Math.min(maxR, Math.max(minR, minR + ((homesActive / maxHomes) * (maxR - minR))));

      const ring = L.circleMarker([node.latitude, node.longitude], {
        radius,
        fillColor: '#8b5cf6',
        color: '#8b5cf6',
        weight: 0,
        fillOpacity: 0.15,
        pane: 'densityPane',
      });

      ring.addTo(layer);
    });
  }, [nodes]);

  // Render node markers (existing logic)
  useEffect(() => {
    if (!mapRef.current || nodes.length === 0) {
      return;
    }

    const map = mapRef.current;
    const layer = nodeLayerRef.current;

    // Only create markers once
    if (markersRef.current.size === 0 && layer) {
      // Add all node markers
      nodes.forEach((node) => {
        const color = getMarkerColor(node.status);

        const marker = L.circleMarker([node.latitude, node.longitude], {
          radius: 4,
          fillColor: color,
          color: color,
          weight: 1,
          opacity: 1,
          fillOpacity: 0.8,
          pane: 'nodePane',
        });

        // Add tooltip (shows on hover)
        marker.bindTooltip(
          `<div class="text-sm">
            <strong>${node.node_id}</strong><br/>
            Status: ${node.status}<br/>
            City: ${node.city}
          </div>`,
          {
            direction: 'top',
            offset: [0, -5],
          }
        );

        // Handle click - use nodesRef to always get the latest node data
        const nodeId = node.node_id;
        marker.on('click', () => {
          const currentNode = nodesRef.current.get(nodeId);
          if (currentNode) {
            onNodeClick(currentNode);
          }
        });

        marker.addTo(layer);
        markersRef.current.set(node.node_id, marker);
      });

      // Force map to invalidate size and redraw
      map.invalidateSize();
  } else {
    // Efficiently update marker colors and visibility using Map lookup (O(1) instead of O(n))
    const nodeMap = new Map(nodes.map((t) => [t.node_id, t]));
    const statusFilterChanged = statusFilter !== prevStatusFilterRef.current;
    const now = Date.now();

    markersRef.current.forEach((marker, nodeId) => {
      const node = nodeMap.get(nodeId);

      if (!node) {
        // Node is filtered out - hide the marker and track for cleanup
        const hiddenSince = hiddenMarkersTimeRef.current.get(nodeId) || now;
        hiddenMarkersTimeRef.current.set(nodeId, hiddenSince);

        // Remove marker if hidden for more than 60 seconds (memory cleanup)
        if (now - hiddenSince > 60000) {
          marker.remove();
          markersRef.current.delete(nodeId);
          hiddenMarkersTimeRef.current.delete(nodeId);
          prevNodeStatusRef.current.delete(nodeId);
          return;
        }

        marker.setStyle({
          opacity: 0,
          fillOpacity: 0
        });
        return;
      }

      // Clear from hidden tracking if visible - but remember if it was hidden
      const wasHidden = hiddenMarkersTimeRef.current.has(nodeId);
      hiddenMarkersTimeRef.current.delete(nodeId);

      const prevStatus = prevNodeStatusRef.current.get(nodeId);

      // Only update if status changed, filter changed, or marker was previously hidden
      if (node.status === prevStatus && !statusFilterChanged && !wasHidden) {
        return; // Skip update - no change
      }

      const color = getMarkerColor(node.status);

      // Check if node should be visible based on status filter
      const isIssue = node.status === NodeStatus.DEGRADED || node.status === NodeStatus.OUTAGE;
      const shouldShow = statusFilter === 'all' ||
                        (statusFilter === 'issues' && isIssue) ||
                        (statusFilter === 'healthy' && node.status === NodeStatus.HEALTHY);

      // Update both fill and stroke colors for visibility
      marker.setStyle({
        fillColor: color,
        color: color,
        opacity: shouldShow ? 1 : 0.1,
        fillOpacity: shouldShow ? 0.8 : 0.05
      });

      // Update tooltip with current status
      marker.setTooltipContent(
        `<div class="text-sm">
          <strong>${node.node_id}</strong><br/>
          Status: <span style="color: ${color}; font-weight: bold;">${node.status.toUpperCase()}</span><br/>
          City: ${node.city}
        </div>`
      );

      // Track new status
      prevNodeStatusRef.current.set(nodeId, node.status);
    });

    // Update previous filter ref
    prevStatusFilterRef.current = statusFilter;
  }
}, [nodes, onNodeClick, statusFilter]);

  return <div id="map" className="w-full h-full" />;
});

GlobalMap.displayName = 'GlobalMap';

export default GlobalMap;
