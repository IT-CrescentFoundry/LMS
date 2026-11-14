# Crescent Foundry LMS — Frontend

React + TypeScript single-page application built with Vite and Tailwind CSS v4. See the [root README](../README.md) for full setup, the [system architecture §4](../docs/architecture/LMS_SYSTEM_ARCHITECTURE.md) for design, the [API reference](../docs/architecture/API_REFERENCE.md) for the backend contract and [ADR-050](../docs/decisions/ARCHITECTURAL_DECISIONS.md) for the authentication design.

## Layout

```text
src/
├── app/          providers (TanStack Query + AuthProvider), router (route table), navigation model
├── layouts/      AppLayout (header, sidebar, mobile drawer, user menu), SidebarNav, AuthLayout (sign-in frame)
├── features/     auth/, admin/, organisation/, dashboard/, system-status/, errors/
├── components/   shared UI (LanguageSelector, ConnectivityIndicator, Loading/Error states, badges, form styles, Modal)
├── hooks/        cross-feature hooks (useMediaQuery)
├── services/     typed API functions (healthService, authService, adminService, organisationService)
├── lib/          apiClient (typed fetch, ApiError, CSRF), parse (response guards), format, config
├── i18n/         i18next setup, languages, locales/{en,bn,hi,gu}/common.json
├── styles/       Tailwind entry and design tokens (navy brand, gold, ember)
├── types/        shared types (API contracts, env)
└── test/         test setup and helpers (renderApp, mockApi, synthetic fixtures incl. orgFixtures)
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
| `/organisation` | `organisation.view` | Organisation Builder: structure tree as of a date, unit details, children and placement history. Changes need `organisation.manage`. |
| `/organisation/unit-types` | `organisation.view` | Unit types, parent rules (advisory / strict), employee-assignment flag. Changes need `organisation.manage`. |
| `/organisation/locations` | `organisation.view` | Physical sites. Changes need `organisation.manage`. |
| `/organisation/job-families`, `/grades`, `/levels`, `/designations` | `organisation.view` | Reference lists (grades and levels are independent). Changes need `designations.manage`. |
| `/organisation/functional-roles` | `organisation.view` | Functional roles (not access roles). Changes, and designation-to-role mappings, need `functional_roles.manage`. |
| `/organisation/responsibilities` | `organisation.view` | Duties catalogue (grants no permission). Changes need `responsibilities.manage`. |

- Screens and navigation items check **permission codes** (`src/features/auth/permissions.ts`), never role names.
- **Hiding a link or page is not a security boundary.** The API enforces every permission itself; the UI only avoids showing screens that would fail. A 403 from the API makes the UI re-read the session.
- The backend records every audit-log read as an `audit.events.viewed` event, so the Audit log page fetches only on open, filter, **Refresh** and **Load more**. It never refetches on window focus. Its request is deliberately not tied to the query's abort signal, so React StrictMode's development remount reuses the in-flight request instead of sending (and auditing) a second one.

## Organisation area (Stage C2)

`src/features/organisation/` uses only the Stage C1 API (`/api/v1/org`, see the [API reference §7–8](../docs/architecture/API_REFERENCE.md)); no backend behaviour is reimplemented in the browser.

| Topic | Design |
|---|---|
| Server state | `orgQueries.ts`: every query key starts with `org`; a successful change invalidates them all, so the tree, details, history and pickers stay consistent with the server. Mutations never retry. |
| Pages | Loaded on first visit (route `lazy`), so users who never open the area never download it. `OrganisationLayout` adds breadcrumbs and the section navigation. |
| Tree | `tree.ts` (pure) rebuilds the hierarchy from `GET /org/tree`; `OrgTree.tsx` implements the WAI-ARIA tree pattern (roving tabindex; arrows, Home/End, Enter/Space). Below the `lg` breakpoint `MobileUnitBrowser` provides one-level-at-a-time drill-down instead. Moving a unit is a form, never drag-and-drop only. |
| As-of date | Blank means "today" on the server (business date); the response's `as_of` is shown. Status views map to `include_closed`; type, status and text filters run on the loaded tree and keep matching units' ancestors visible. |
| Changes | Correct (PATCH, only changed fields, with `version` and a reason), move and close (two-step confirmation with an effective date), reopen. Units are never deleted. Advisory-rule warnings are shown with the success message; strict-rule and other refusals show the translated error, and closures list the blocking dependants returned by the API. |
| Conflicts | A `409 version_conflict` is never retried or overwritten: the dialog offers **Reload the latest data**, which refreshes every organisation view and closes the dialog. |
| Permissions | Each page reads `organisation.view`; write controls appear only with the matching `*.manage` code (read-only users see a **Read only** badge). The API enforces both. |
| Names | Translated display names (`bn`, `hi`, `gu`) are used in the UI language, falling back to the recorded name (`names.ts`). |
| Errors | `orgErrors.ts` lists every C1 error code; each is translated in all four languages (`org.errors.codes.*`). The backend's English message is never shown. |
| Dialogs | `components/Modal.tsx`: labelled `role="dialog"`, focus moves in and returns to the opener, Tab is trapped, Escape closes (not while saving), backdrop clicks do not discard input. |

## Testing

- `src/test/renderApp.tsx` renders the real app with a memory router. `mockApi()` stubs `fetch` with a route table (`'GET /auth/session'`, …) and records every request, including headers and bodies. `mockSignedIn(user)` adds a signed-in session.
- Fixtures (`EMPLOYEE`, `SUPERVISOR`, `HR_ADMIN`, `SUPER_ADMIN`, `sessionBody`, and `orgFixtures.ts`) are synthetic. The only real organisation names are the five approved baseline functions. Never use real employee data.
- `src/test/setup.ts` clears web storage, the in-memory CSRF token and the auth handlers after each test.

## Adding translations

1. Add the key and English text to `src/i18n/locales/en/common.json` (keys are type-checked against this file).
2. Add the same key to `bn`, `hi` and `gu`. `src/i18n/i18n.test.ts` fails if any language is missing a key, has an empty value or drops an `{{placeholder}}`.
3. Translate backend error **codes** (see `src/features/auth/authErrors.ts`); never show the backend's English `message` to users.
4. Have new strings reviewed by a native speaker before learner-facing release. The Stage B6 and C2 Bengali, Hindi and Gujarati strings are still awaiting that review.
