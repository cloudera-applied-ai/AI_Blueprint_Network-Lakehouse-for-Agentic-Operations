import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    {
      name: 'disable-host-check',
      configureServer(server) {
        // Intercept at the HTTP server level, before Vite's middleware
        const originalListeners = server.httpServer?.listeners('request').slice() || [];
        server.httpServer?.removeAllListeners('request');

        server.httpServer?.on('request', (req, res) => {
          // Override the host header for all requests
          if (req.headers.host) {
            req.headers.host = 'localhost:8100';
          }
          // Call original listeners
          originalListeners.forEach(listener => listener(req, res));
        });
      },
    },
    {
      name: 'csp-headers',
      configureServer(server) {
        server.middlewares.use((_req, res, next) => {
          // Allow Cloudera Agent Studio iframe
          res.setHeader(
            'Content-Security-Policy',
            "default-src 'self'; " +
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; " +
            "style-src 'self' 'unsafe-inline'; " +
            "img-src 'self' data: blob: https:; " +
            "font-src 'self' data:; " +
            "connect-src 'self' ws: wss: http: https:; " +
            "frame-src 'self' https://*.cloudera.site https://*.cloudera.com;"
          );
          next();
        });
      },
    },
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0', // Listen on all addresses
    strictPort: false,
    hmr: false, // Disable HMR to bypass host checking
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: '0.0.0.0',
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
