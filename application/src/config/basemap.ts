/**
 * Basemap configuration for the Leaflet map.
 *
 * Resolution order (first non-empty wins):
 *   1. System settings saved from the UI (Settings -> Map Basemap), stored in
 *      the backend `system_settings` table: carto_api_key / carto_basemap.
 *   2. Vite env vars baked in at build time:
 *        VITE_CARTO_API_KEY    - CARTO API key / access token
 *        VITE_CARTO_BASEMAP    - style: light_all (default), dark_all, voyager,
 *                                light_nolabels, dark_nolabels, ...
 *        VITE_BASEMAP_TILE_URL - full tile URL template override; supports the
 *                                Leaflet placeholders plus {token}
 */
import { systemSettingsService } from '../services/systemSettingsService';

const env = import.meta.env;

export const ENV_CARTO_API_KEY: string = (env.VITE_CARTO_API_KEY || '').trim();
export const ENV_CARTO_BASEMAP: string = (env.VITE_CARTO_BASEMAP || 'light_all').trim();

export const CARTO_BASEMAP_STYLES = [
  { value: 'light_all', label: 'Positron (light)' },
  { value: 'light_nolabels', label: 'Positron (light, no labels)' },
  { value: 'dark_all', label: 'Dark Matter' },
  { value: 'dark_nolabels', label: 'Dark Matter (no labels)' },
  { value: 'rastertiles/voyager', label: 'Voyager' },
  { value: 'rastertiles/voyager_nolabels', label: 'Voyager (no labels)' },
] as const;

export function resolveCartoApiKey(): string {
  const saved = systemSettingsService.getSettings()?.carto_api_key;
  return (saved && saved.trim()) || ENV_CARTO_API_KEY;
}

export function resolveCartoBasemap(): string {
  const saved = systemSettingsService.getSettings()?.carto_basemap;
  return (saved && saved.trim()) || ENV_CARTO_BASEMAP;
}

export function basemapTileUrl(): string {
  const key = resolveCartoApiKey();
  const override = (env.VITE_BASEMAP_TILE_URL || '').trim();
  let url = override || `https://{s}.basemaps.cartocdn.com/${resolveCartoBasemap()}/{z}/{x}/{y}{r}.png`;

  if (url.includes('{token}')) {
    url = url.replace(/\{token\}/g, encodeURIComponent(key));
  } else if (key) {
    // CARTO basemaps authenticate tile requests with `?key=` (carto.com/basemaps/apikey).
    url += (url.includes('?') ? '&' : '?') + 'key=' + encodeURIComponent(key);
  }
  return url;
}

export const BASEMAP_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';
