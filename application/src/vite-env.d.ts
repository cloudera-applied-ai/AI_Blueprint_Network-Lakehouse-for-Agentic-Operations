/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_AGENT_STUDIO_URL?: string;
  readonly VITE_API_KEY?: string;
  readonly VITE_CARTO_API_KEY?: string;
  readonly VITE_CARTO_BASEMAP?: string;
  readonly VITE_BASEMAP_TILE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
