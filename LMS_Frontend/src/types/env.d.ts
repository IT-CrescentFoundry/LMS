/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL for API calls, e.g. "/api/v1" (same origin) or a full URL. */
  readonly VITE_API_BASE_URL?: string
  /** Connectivity polling interval in milliseconds. */
  readonly VITE_HEALTH_POLL_INTERVAL_MS?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
