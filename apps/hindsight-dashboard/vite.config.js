import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Rely on Vite's native TS/TSX handling; previous esbuild loader override caused TS interface parse errors in Docker build.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/guest-api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/guest-api/, '')
      }
    }
  }
});
