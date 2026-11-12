# Crescent Foundry LMS — Frontend

React + TypeScript single-page application built with Vite and Tailwind CSS v4. See the [root README](../README.md) for full setup and the [system architecture](../docs/architecture/LMS_SYSTEM_ARCHITECTURE.md#4-frontend-architecture--implemented-shell) for design.

## Layout

```text
src/
├── app/          providers (TanStack Query), router (route table), navigation model
├── layouts/      AppLayout (header, sidebar, mobile drawer), SidebarNav
├── features/     dashboard/, system-status/, errors/
├── components/   shared UI (LanguageSelector, ConnectivityIndicator, Loading/Error states)
├── hooks/        cross-feature hooks
├── services/     typed API functions (healthService)
├── lib/          apiClient (typed fetch + ApiError), config (env validation)
├── i18n/         i18next setup, languages, locales/{en,bn,hi,gu}/common.json
├── styles/       Tailwind entry and design tokens
├── types/        shared types (API contracts, env)
└── test/         test setup and helpers
```

## Commands (from `LMS_Frontend/`)

```powershell
npm ci                 # install exact versions from package-lock.json
npm run dev            # http://localhost:5173 (proxies /api to the backend)
npm run typecheck      # TypeScript project build check
npm run lint           # ESLint
npm test               # Vitest (single run)
npm run test:watch     # Vitest (watch mode)
npm run build          # type-check + production build into dist/
npm run preview        # serve dist/ on http://localhost:4173 (also proxies /api)
npm run check          # typecheck + lint + test + build
```

## Configuration

Copy `.env.example` to `.env.local` (git-ignored) to override defaults:

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `/api/v1` | API base used by the browser. |
| `VITE_HEALTH_POLL_INTERVAL_MS` | `30000` | Connectivity re-check interval (min 5000). |
| `LMS_DEV_API_PROXY_TARGET` | `http://127.0.0.1:8000` | Dev/preview proxy target (not exposed to the browser). |

`VITE_*` values are embedded in the browser bundle — never put secrets in them.

## Adding translations

1. Add the key and English text to `src/i18n/locales/en/common.json` (keys are type-checked against this file).
2. Add the same key to `bn`, `hi` and `gu`. `src/i18n/i18n.test.ts` fails if any language is missing a key or has an empty value.
3. Have new strings reviewed by a native speaker before learner-facing release.
