# Crescent Foundry LMS — Frontend

React + TypeScript single-page application built with Vite and Tailwind CSS v4. See the [root README](../README.md) for full setup, the [system architecture §4](../docs/architecture/LMS_SYSTEM_ARCHITECTURE.md) for design, the [API reference](../docs/architecture/API_REFERENCE.md) for the backend contract and [ADR-050](../docs/decisions/ARCHITECTURAL_DECISIONS.md) for the authentication design.

## Layout

```text
src/
├── app/          providers (TanStack Query + AuthProvider), router (route table), navigation model
├── layouts/      AppLayout (header, sidebar, mobile drawer, user menu), SidebarNav, AuthLayout (sign-in frame)
├── features/     auth/, admin/, dashboard/, system-status/, errors/
├── components/   shared UI (LanguageSelector, ConnectivityIndicator, Loading/Error states, badges, form styles)
├── hooks/        cross-feature hooks
├── services/     typed API functions (healthService, authService, adminService)
├── lib/          apiClient (typed fetch, ApiError, CSRF), parse (response guards), format, config
├── i18n/         i18next setup, languages, locales/{en,bn,hi,gu}/common.json
├── styles/       Tailwind entry and design tokens (navy brand, gold, ember)
├── types/        shared types (API contracts, env)
└── test/         test setup and helpers (renderApp, mockApi, synthetic fixtures)
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

### Running against the backend locally

1. Start the API from `LMS_Backend/` (see the root README). Its `.env` must list the address you open in the browser in `LMS_TRUSTED_ORIGINS` (for example `http://localhost:5173,http://127.0.0.1:5173`), and set `LMS_SESSION_COOKIE_SECURE=false` for plain-http development.
2. `npm run dev` and open `http://localhost:5173`.
3. Opening the app from any other address (for example a phone using the PC's LAN IP) makes sign-in fail with "Sign-in is not allowed from this web address" until that origin is added to `LMS_TRUSTED_ORIGINS`.

## Authentication and sessions

| Concern | How it works |
|---|---|
| Session | Server-side. The backend sets an **HttpOnly** cookie (`lms_session`, or `__Host-lms_session` when Secure). JavaScript never sees it; requests are same-origin with `credentials: 'same-origin'`. |
| Sign-in | `POST /api/v1/auth/login {login_id, password}`. No CSRF token is needed: the backend checks the browser's `Origin` header against `LMS_TRUSTED_ORIGINS`. |
| CSRF | Login, `GET /auth/session` and password change return a session-bound `csrf_token`. `src/lib/apiClient.ts` keeps it **in memory only** and sends it as `X-CSRF-Token` on POST/PUT/PATCH/DELETE. On `403 csrf_failed` it re-reads the session once and retries once. |
| Restore after reload | `AuthProvider` calls `GET /api/v1/auth/session` (public; does not extend the idle timeout) to restore the user, permissions and CSRF token. It re-checks on window focus and when the server's idle/absolute expiry passes. |
| Ended session | Any `401 unauthenticated` returns the user to `/login` with "Your session has ended", remembering the page they were on. |
| Sign-out | `POST /api/v1/auth/logout`, then every cached query except health is removed, so nothing from the previous user stays in memory. |
| Password change | `/change-password` (`POST /auth/password`). Forced while `password_must_change` is set; the response rotates the session and CSRF token. |
| Storage | `localStorage` holds only the language preference (`lms.language`). Tokens, passwords and user data are never written to web storage, and request bodies are never logged. |

Response parsers (`src/services/*`) copy only known fields, so an unexpected field (for example a hash) is dropped before it reaches the cache or the UI.

## Routes and permissions

| Route | Guard | Notes |
|---|---|---|
| `/login` | public (signed-in users are sent on) | Post-login redirect only to an internal path held in router state, never a URL parameter. |
| `/change-password` | signed in | Forced when a password change is required. |
| `/` | signed in | Dashboard. |
| `/admin/users` | `user_accounts.view` | Read-only account directory (`GET /admin/users`). |
| `/admin/audit-log` | `audit.view` | Read-only audit log (`GET /admin/audit-events`). |

- Screens and navigation items check **permission codes** (`src/features/auth/permissions.ts`), never role names.
- **Hiding a link or page is not a security boundary.** The API enforces every permission itself; the UI only avoids showing screens that would fail. A 403 from the API makes the UI re-read the session.
- The backend records every audit-log read as an `audit.events.viewed` event, so the Audit log page fetches only on open, filter, **Refresh** and **Load more**. It never refetches on window focus. Its request is deliberately not tied to the query's abort signal, so React StrictMode's development remount reuses the in-flight request instead of sending (and auditing) a second one.

## Testing

- `src/test/renderApp.tsx` renders the real app with a memory router. `mockApi()` stubs `fetch` with a route table (`'GET /auth/session'`, …) and records every request, including headers and bodies. `mockSignedIn(user)` adds a signed-in session.
- Fixtures (`EMPLOYEE`, `HR_ADMIN`, `SUPER_ADMIN`, `sessionBody`) are synthetic. Never use real employee data.
- `src/test/setup.ts` clears web storage, the in-memory CSRF token and the auth handlers after each test.

## Adding translations

1. Add the key and English text to `src/i18n/locales/en/common.json` (keys are type-checked against this file).
2. Add the same key to `bn`, `hi` and `gu`. `src/i18n/i18n.test.ts` fails if any language is missing a key, has an empty value or drops an `{{placeholder}}`.
3. Translate backend error **codes** (see `src/features/auth/authErrors.ts`); never show the backend's English `message` to users.
4. Have new strings reviewed by a native speaker before learner-facing release. The Stage B6 Bengali, Hindi and Gujarati strings are still awaiting that review.
