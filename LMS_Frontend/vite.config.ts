/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Loads .env files for use in this config only. Only VITE_* variables are
  // ever exposed to browser code.
  const env = loadEnv(mode, process.cwd(), '')
  const apiProxyTarget = env.LMS_DEV_API_PROXY_TARGET || 'http://127.0.0.1:8000'

  // The browser calls /api on the same origin; the dev/preview server forwards
  // those requests to the FastAPI backend. This mirrors the recommended
  // production setup (one origin, reverse proxy) and keeps future session
  // cookies first-party.
  const proxy = { '/api': { target: apiProxyTarget, changeOrigin: false } }

  return {
    plugins: [react(), tailwindcss()],
    server: { port: 5173, strictPort: true, proxy },
    preview: { port: 4173, strictPort: true, proxy },
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      restoreMocks: true,
      unstubGlobals: true,
    },
  }
})
