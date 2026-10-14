import { QueryCache, CachedQuery } from '@/types';

// Query cache instance (singleton pattern for efficiency)
let queryCache: QueryCache | null = null;

export const getQueryCache = (): QueryCache => {
  if (!queryCache) {
    queryCache = new Map();
  }
  return queryCache;
};

// Efficient cache helper with TTL
export const getCachedData = <T>(
  key: string,
  fetcher: () => T,
  ttl: number
): T => {
  const cache = getQueryCache();
  const cached = cache.get(key) as CachedQuery<T> | undefined;

  const now = Date.now();

  if (cached && now - cached.timestamp < cached.ttl) {
    return cached.data;
  }

  const data = fetcher();
  cache.set(key, {
    data,
    timestamp: now,
    ttl,
  });

  return data;
};

// Clear expired cache entries (run periodically)
export const clearExpiredCache = (): void => {
  const cache = getQueryCache();
  const now = Date.now();

  for (const [key, value] of cache.entries()) {
    if (now - value.timestamp >= value.ttl) {
      cache.delete(key);
    }
  }
};

// Invalidate specific cache keys (call after backend refresh)
export const invalidateCache = (keys?: string[]): void => {
  const cache = getQueryCache();
  if (keys) {
    keys.forEach(key => cache.delete(key));
  } else {
    // Invalidate all data caches (not the entire cache)
    const keysToDelete = ['active_alerts', 'network_health'];
    // Also invalidate any actions cache entries
    for (const key of cache.keys()) {
      if (key.startsWith('recent_actions_')) {
        keysToDelete.push(key);
      }
    }
    keysToDelete.forEach(key => cache.delete(key));
  }
};

// Generate unique ID efficiently
let idCounter = 0;
export const generateId = (prefix: string): string => {
  return `${prefix}-${Date.now()}-${(idCounter++).toString(36)}`;
};

// Generate node ID with region-based numbering
export const generateNodeId = (regionIndex: number, nodeIndex: number): string => {
  return `CELL-${regionIndex.toString().padStart(2, '0')}${nodeIndex.toString().padStart(4, '0')}`;
};

// Random number generators (optimized with closure)
export const randomInRange = (min: number, max: number): number => {
  return Math.random() * (max - min) + min;
};

export const randomInt = (min: number, max: number): number => {
  return Math.floor(randomInRange(min, max + 1));
};

export const randomChoice = <T>(array: T[]): T => {
  return array[Math.floor(Math.random() * array.length)];
};

export const randomChoices = <T>(array: T[], count: number): T[] => {
  const shuffled = [...array].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, count);
};

// Weighted random choice for realistic distributions
export const weightedRandomChoice = <T>(
  items: T[],
  weights: number[]
): T => {
  const totalWeight = weights.reduce((sum, weight) => sum + weight, 0);
  let random = Math.random() * totalWeight;

  for (let i = 0; i < items.length; i++) {
    random -= weights[i];
    if (random <= 0) {
      return items[i];
    }
  }

  return items[items.length - 1];
};

// Time-based patterns for realistic data
export const getHourlyTrafficMultiplier = (hour: number): number => {
  // Peak hours: 8-10 AM and 5-7 PM
  if ((hour >= 8 && hour <= 10) || (hour >= 17 && hour <= 19)) {
    return 1.5;
  }
  // Off-peak: midnight to 6 AM
  if (hour >= 0 && hour <= 6) {
    return 0.4;
  }
  // Normal hours
  return 1.0;
};

export const getDayOfWeekMultiplier = (dayOfWeek: number): number => {
  // Weekend (0 = Sunday, 6 = Saturday)
  if (dayOfWeek === 0 || dayOfWeek === 6) {
    return 0.8;
  }
  // Weekday
  return 1.0;
};

// Format numbers for display
export const formatNumber = (num: number, decimals: number = 0): string => {
  return num.toFixed(decimals);
};

export const formatPercentage = (num: number, decimals: number = 1): string => {
  return `${num.toFixed(decimals)}%`;
};

export const formatBytes = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
};

// Date formatting
export const formatTimestamp = (date: Date): string => {
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

export const formatDuration = (seconds: number): string => {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
};

// Color mapping for status
export const getStatusColor = (status: string): string => {
  const colors: Record<string, string> = {
    healthy: 'text-green-600 bg-green-100',
    degraded: 'text-yellow-600 bg-yellow-100',
    outage: 'text-red-600 bg-red-100',
    maintenance: 'text-gray-600 bg-gray-100',
    critical: 'text-red-600 bg-red-100',
    warning: 'text-yellow-600 bg-yellow-100',
    info: 'text-blue-600 bg-blue-100',
    active: 'text-red-600 bg-red-100',
    acknowledged: 'text-yellow-600 bg-yellow-100',
    resolved: 'text-green-600 bg-green-100',
    pending: 'text-gray-600 bg-gray-100',
    in_progress: 'text-blue-600 bg-blue-100',
    completed: 'text-green-600 bg-green-100',
    failed: 'text-red-600 bg-red-100',
  };
  return colors[status.toLowerCase()] || 'text-gray-600 bg-gray-100';
};

export const getMarkerColor = (status: string): string => {
  const colors: Record<string, string> = {
    healthy: '#10b981',
    degraded: '#f59e0b',
    outage: '#ef4444',
    maintenance: '#6b7280',
  };
  return colors[status.toLowerCase()] || '#6b7280';
};

// Debounce function for performance
export const debounce = <T extends (...args: unknown[]) => unknown>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout | null = null;

  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
};

// Throttle function for performance
export const throttle = <T extends (...args: unknown[]) => unknown>(
  func: T,
  limit: number
): ((...args: Parameters<T>) => void) => {
  let inThrottle: boolean;

  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
};

// Calculate percentile (for KPI aggregations)
export const percentile = (arr: number[], p: number): number => {
  if (arr.length === 0) return 0;
  const sorted = [...arr].sort((a, b) => a - b);
  const index = (p / 100) * (sorted.length - 1);
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  const weight = index % 1;

  if (lower === upper) {
    return sorted[lower];
  }

  return sorted[lower] * (1 - weight) + sorted[upper] * weight;
};

// Calculate moving average for smoothing
export const movingAverage = (data: number[], window: number): number[] => {
  const result: number[] = [];
  for (let i = 0; i < data.length; i++) {
    const start = Math.max(0, i - window + 1);
    const subset = data.slice(start, i + 1);
    const avg = subset.reduce((sum, val) => sum + val, 0) / subset.length;
    result.push(avg);
  }
  return result;
};

// Calculate healing action progress percentage
export const calculateActionProgress = (action: {
  status: string;
  timestamp: Date;
  completion_time?: Date;
}): number => {
  const now = new Date();
  const actionAge = now.getTime() - action.timestamp.getTime();

  if (action.status === 'completed' || action.status === 'failed' || action.status === 'rolled_back') {
    return 100;
  }

  if (action.status === 'pending') {
    // Pending for 3 seconds before starting (initialization phase)
    return Math.min((actionAge / 3000) * 10, 10); // 0-10% during pending
  }

  if (action.status === 'in_progress') {
    // In progress takes 25 seconds total (from healingEngine.ts)
    const progressAge = actionAge - 3000; // Subtract the pending time
    const progressPercent = ((progressAge / 22000) * 89) + 10; // 10-99% during execution
    return Math.min(progressPercent, 99); // Cap at 99% until completed
  }

  return 0;
};

// ===== DEVELOPMENT LOGGING UTILITY =====
// Production-safe logging that can be easily disabled

const isDevelopment = import.meta.env?.DEV ?? process.env.NODE_ENV !== 'production';

interface DevLogger {
  debug: (...args: unknown[]) => void;
  info: (...args: unknown[]) => void;
  warn: (...args: unknown[]) => void;
  error: (...args: unknown[]) => void;
  log: (...args: unknown[]) => void;
}

/**
 * Development-only logger that's automatically disabled in production.
 * Use this instead of console.log for debug output.
 *
 * Usage:
 *   import { devLog } from '@/utils/helpers';
 *   devLog.info('Loading data...', { count: 100 });
 *   devLog.error('Failed to fetch', error);
 */
export const devLog: DevLogger = {
  debug: (...args: unknown[]) => {
    if (isDevelopment) console.debug('[DEV]', ...args);
  },
  info: (...args: unknown[]) => {
    if (isDevelopment) console.log('[INFO]', ...args);
  },
  warn: (...args: unknown[]) => {
    if (isDevelopment) console.warn('[WARN]', ...args);
  },
  error: (...args: unknown[]) => {
    // Always log errors, even in production
    console.error('[ERROR]', ...args);
  },
  log: (...args: unknown[]) => {
    if (isDevelopment) console.log(...args);
  },
};
