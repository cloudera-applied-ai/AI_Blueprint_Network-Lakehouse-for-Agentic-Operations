import { Clock } from 'lucide-react';

export type TimeRange = '1h' | '6h' | '24h' | '7d' | '30d';

interface TimeRangeSelectorProps {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
  loading?: boolean;
  className?: string;
}

const TIME_RANGES: { value: TimeRange; label: string; hours: number }[] = [
  { value: '1h', label: '1H', hours: 1 },
  { value: '6h', label: '6H', hours: 6 },
  { value: '24h', label: '24H', hours: 24 },
  { value: '7d', label: '7D', hours: 168 },
  { value: '30d', label: '30D', hours: 720 },
];

export function TimeRangeSelector({ value, onChange, loading, className = '' }: TimeRangeSelectorProps) {
  return (
    <div className={`flex items-center gap-1 ${className}`}>
      <Clock className="w-4 h-4 text-gray-400 mr-1" />
      <div className="flex bg-gray-800 rounded-lg p-0.5">
        {TIME_RANGES.map((range) => (
          <button
            key={range.value}
            onClick={() => onChange(range.value)}
            disabled={loading}
            className={`
              px-2 py-1 text-xs font-medium rounded-md transition-all duration-200
              ${value === range.value
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-gray-400 hover:text-white hover:bg-gray-700'
              }
              ${loading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
            `}
          >
            {range.label}
          </button>
        ))}
      </div>
      {loading && (
        <span className="ml-2 text-xs text-gray-400 animate-pulse">
          Loading...
        </span>
      )}
    </div>
  );
}

/**
 * Convert time range to hours for API calls
 */
export function timeRangeToHours(range: TimeRange): number {
  const found = TIME_RANGES.find(r => r.value === range);
  return found ? found.hours : 1;
}

/**
 * Convert time range to days for API calls
 */
export function timeRangeToDays(range: TimeRange): number {
  return Math.ceil(timeRangeToHours(range) / 24);
}

export default TimeRangeSelector;
