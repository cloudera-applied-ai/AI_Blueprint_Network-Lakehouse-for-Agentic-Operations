import { useState, memo } from 'react';
import { Layers, ChevronDown, ChevronUp } from 'lucide-react';
import type { MapLayerVisibility } from './GlobalMap';

interface LayerDef {
  key: keyof MapLayerVisibility;
  label: string;
  count?: number;
  icon: React.ReactNode;
  defaultOff?: boolean;
}

interface MapLayerControlProps {
  layerVisibility: MapLayerVisibility;
  onVisibilityChange: (visibility: MapLayerVisibility) => void;
  headendCount?: number;
  hubCount?: number;
  nodeCount?: number;
}

const MapLayerControl = memo(({
  layerVisibility,
  onVisibilityChange,
  headendCount = 0,
  hubCount = 0,
  nodeCount = 0,
}: MapLayerControlProps) => {
  const [expanded, setExpanded] = useState(false);

  const layers: LayerDef[] = [
    {
      key: 'headends',
      label: 'Headends',
      count: headendCount,
      icon: (
        <div className="w-4 h-4 bg-emerald-500 border-2 border-white rounded-sm flex-shrink-0" />
      ),
    },
    {
      key: 'hubs',
      label: 'Hubs',
      count: hubCount,
      icon: (
        <div className="w-3.5 h-3.5 bg-emerald-500 border border-white rounded-sm flex-shrink-0"
          style={{ transform: 'rotate(45deg)' }}
        />
      ),
    },
    {
      key: 'nodes',
      label: 'Fiber Nodes',
      count: nodeCount,
      icon: (
        <div className="w-3 h-3 bg-emerald-500 rounded-full border border-white flex-shrink-0" />
      ),
    },
    {
      key: 'customerDensity',
      label: 'Customer Density',
      icon: (
        <div className="w-4 h-4 rounded-full bg-purple-500/30 border border-purple-400/50 flex-shrink-0" />
      ),
      defaultOff: true,
    },
  ];

  const toggle = (key: keyof MapLayerVisibility) => {
    onVisibilityChange({ ...layerVisibility, [key]: !layerVisibility[key] });
  };

  return (
    <div className="absolute top-4 left-4 z-[1000]">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg shadow-lg hover:bg-gray-750 transition-colors text-gray-200 text-sm font-medium"
      >
        <Layers className="w-4 h-4" />
        Layers
        {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
      </button>

      {expanded && (
        <div className="mt-1 bg-gray-800 border border-gray-700 rounded-lg shadow-lg p-3 min-w-[200px]">
          <div className="space-y-2">
            {layers.map(({ key, label, count, icon }) => (
              <label
                key={key}
                className="flex items-center gap-3 cursor-pointer hover:bg-gray-700/50 rounded px-2 py-1.5 transition-colors"
              >
                {icon}
                <span className="text-sm text-gray-300 flex-1">{label}</span>
                {count !== undefined && count > 0 && (
                  <span className="text-xs text-gray-500">{count}</span>
                )}
                <input
                  type="checkbox"
                  checked={layerVisibility[key]}
                  onChange={() => toggle(key)}
                  className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-600 focus:ring-blue-500 focus:ring-offset-0 cursor-pointer"
                />
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
});

MapLayerControl.displayName = 'MapLayerControl';

export default MapLayerControl;
