import { useState, useEffect } from 'react';
import { pauseSystem, resumeSystem, getSystemStatus } from '@/services/apiClient';

interface UseSystemPauseReturn {
  /** Whether the system is currently paused */
  paused: boolean;
  /** Whether a pause/resume operation is in progress */
  loading: boolean;
  /** Toggle between paused and resumed states */
  togglePause: () => Promise<void>;
}

/**
 * Manages the system pause/resume state for data generation and LLM queries.
 *
 * On mount (once `initializing` becomes false), fetches the current pause state
 * from the backend. Provides a toggle function that calls the backend
 * pause/resume endpoints.
 */
export function useSystemPause(initializing: boolean): UseSystemPauseReturn {
  const [paused, setPaused] = useState(false);
  const [loading, setLoading] = useState(false);

  // Fetch initial system status after app finishes loading
  useEffect(() => {
    if (initializing) return;

    const fetchSystemStatus = async () => {
      try {
        const status = await getSystemStatus();
        const isPaused = status.data_generation.paused || status.llm.paused;
        setPaused(isPaused);
        if (isPaused) {
          console.log('System is currently PAUSED');
        }
      } catch (error) {
        // Backend might not support this endpoint yet
        console.debug('Could not fetch system status:', error);
      }
    };

    fetchSystemStatus();
  }, [initializing]);

  const togglePause = async () => {
    setLoading(true);
    try {
      if (paused) {
        await resumeSystem({ dataGeneration: true, llm: true });
        setPaused(false);
        console.log('System RESUMED - data generation and AI analysis active');
      } else {
        await pauseSystem({ dataGeneration: true, llm: true });
        setPaused(true);
        console.log('System PAUSED - data generation and AI analysis stopped');
      }
    } catch (error) {
      console.error('Failed to toggle system pause:', error);
    } finally {
      setLoading(false);
    }
  };

  return {
    paused,
    loading,
    togglePause,
  };
}
