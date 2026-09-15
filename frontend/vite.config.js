import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '127.0.0.1',
    proxy: {
      '/auth': 'http://127.0.0.1:8001',
      '/projects': 'http://127.0.0.1:8001',
      '/land-records': 'http://127.0.0.1:8001',
      '/dashboard': 'http://127.0.0.1:8001',
      '/gis': 'http://127.0.0.1:8001',
      '/documents': 'http://127.0.0.1:8001',
      '/ocr': 'http://127.0.0.1:8001',
      '/alerts': 'http://127.0.0.1:8001',
      '/audit': 'http://127.0.0.1:8001',
      '/citizen': 'http://127.0.0.1:8001',
      '/field': 'http://127.0.0.1:8001',
      '/analytics': 'http://127.0.0.1:8001',
      '/sla': 'http://127.0.0.1:8001',
      '/reports': 'http://127.0.0.1:8001',
      '/grievances': 'http://127.0.0.1:8001',
      '/compensation': 'http://127.0.0.1:8001',
      '/intelligence': 'http://127.0.0.1:8001',
      '/rr': 'http://127.0.0.1:8001',
      '/sms': 'http://127.0.0.1:8001',
      '/privacy': 'http://127.0.0.1:8001',
      '/data-quality': 'http://127.0.0.1:8001',
      '/api': 'http://127.0.0.1:8001'
    }
  },
  build: {
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/leaflet') || id.includes('node_modules/react-leaflet')) {
            return 'vendor-leaflet';
          }
          if (id.includes('node_modules/recharts')) {
            return 'vendor-recharts';
          }
          if (id.includes('node_modules/react') || id.includes('node_modules/react-dom')) {
            return 'vendor-react';
          }
        }
      }
    }
  }
});
