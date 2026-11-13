# LMS API Reference (Stage B)

| | |
|---|---|
| **Status** | Implemented. Every endpoint below exists in `LMS_Backend/app/api/routes/`. This list is checked against the routes registered by `create_app()`. |
| **Base path** | `/api/v1` (served on the same origin as the SPA; ADR-011) |
| **Machine-readable** | `GET /api/v1/openapi.json` and Swagger UI at `/api/docs` — development only (disabled in production) |
| **Related** | [System architecture §7, §11](LMS_SYSTEM_ARCHITECTURE.md) · [Decisions ADR-040…050](../decisions/ARCHITECTURAL_DECISIONS.md) · [Database design §4](../database/LMS_DATABASE_DESIGN.md) |

## 1. Conventions

| Topic | Rule |
|---|---|
| Format | JSON, UTF-8, `snake_case` fields; timestamps ISO 8601 UTC. |
| Identifiers | Resources are addressed by `public_id` (UUIDv7) — never by internal numeric keys (ADR-049). |
| Session | HttpOnly cookie `lms_session` (`__Host-lms_session` when Secure), set by sign-in and password change. Browsers send it automatically; the token is never in a response body (ADR-043). |
| CSRF | **Every** POST/PUT/PATCH/DELETE needs an `Origin` (or `Referer`) listed in `LMS_TRUSTED_ORIGINS`, otherwise `403 origin_not_allowed`. Authenticated state-changing requests also need `X-CSRF-Token: <csrf_token>`, otherwise `403 csrf_failed`. Sign-in needs no token (ADR-044). |
| Authorisation | Deny by default. Each non-public route requires a session and, for administration, a permission code. Missing permission → `403 forbidden` (audited as `authorization.denied`). Accounts that must change their password get `403 password_change_required` on permission-guarded routes. |
| Pagination | `limit` + opaque `cursor`; responses are `{"items": [...], "next_cursor": "…" \| null}`, newest first. Pass `next_cursor` back as `cursor`. A malformed cursor → `422 invalid_cursor`. |
| Errors | `{"error": {"code", "message", "details"?, "request_id"?}}`. `code` is stable and translated by the frontend; `message` is a safe English fallback; validation `details` are `[{location, message, type}]` and never echo submitted values. |
| Request ID | `X-Request-ID` is accepted if well-formed, otherwise generated; always returned. |
| Caching | `Cache-Control: no-store` on every response. |

Common error codes on authenticated routes: `401 unauthenticated` (no/expired/revoked session; the cookie is cleared), `403 csrf_failed`, `403 origin_not_allowed`, `403 forbidden`, `403 password_change_required`, `422 validation_error`.

## 2. Health (public)

| Method | Path | Response |
|---|---|---|
| GET | `/api/v1/health/live` | `200 {status: "ok", service, version, timestamp}` — never touches the database. |
| GET | `/api/v1/health/ready` | `200` / `503 {status: "ready" \| "not_ready", checks: {database: {status: "ok" \| "not_configured" \| "unavailable", detail, duration_ms}}, timestamp}` |

## 3. Authentication

| Method | Path | Access | CSRF token | Request | Success | Errors |
|---|---|---|---|---|---|---|
| POST | `/api/v1/auth/login` | public | none (Origin only) | `{login_id (1–128), password (1–1024)}` | `200 SessionResponse` + session cookie | `401 invalid_credentials`, `403 account_inactive`, `429 too_many_attempts` |
| GET | `/api/v1/auth/session` | public | – | – | `200 SessionResponse` (`authenticated: false` when there is no valid session; a stale cookie is cleared). Does **not** extend the idle timeout. | – |
| GET | `/api/v1/auth/me` | session | – | – | `200 CurrentUser` | `401` |
| POST | `/api/v1/auth/logout` | session | required | – | `204`, cookie cleared | `401`, `403 csrf_failed` |
| POST | `/api/v1/auth/password` | session (allowed while a change is required) | required | `{current_password, new_password}` | `200 SessionResponse` with a **new** session and CSRF token; all other sessions revoked | `400 invalid_current_password`, `422 password_policy` (`details[].type` ∈ `too_short`, `too_long`, `contains_login_id`, `repeated_character`, `too_common`, `same_as_current`), `429 too_many_attempts` |

```text
SessionResponse { authenticated: bool, user: CurrentUser | null, csrf_token: str | null,
                  idle_expires_at: datetime | null, absolute_expires_at: datetime | null }
CurrentUser     { public_id, login_id, display_name, email | null, status,
                  password_must_change: bool, roles: [role_code], permissions: [permission_code] }
```

## 4. Administration — user accounts (`/api/v1/admin/users`)

All require a session; state-changing calls require the CSRF token. Business rules (ADR-046): no administrative action on one's own account; accounts holding permissions the actor lacks cannot be managed; role grants follow the assignment guards.

| Method | Path | Permission | Request | Success |
|---|---|---|---|---|
| GET | `/admin/users` | `user_accounts.view` | query `status?` (`pending_activation` \| `active` \| `suspended` \| `disabled`), `q?` (≤ 100; login ID or name contains), `limit` 1–100 (default 25), `cursor?` | `200 Page[UserSummary]` |
| POST | `/admin/users` | `user_accounts.manage` | `{login_id (2–64), display_name, email?, temporary_password, roles? (default ["employee"])}` | `201 UserDetail` (status `pending_activation`, must change password) |
| GET | `/admin/users/{public_id}` | `user_accounts.view` | – | `200 UserDetail` |
| PATCH | `/admin/users/{public_id}` | `user_accounts.manage` | `{display_name?, email?}` | `200 UserDetail` |
| POST | `/admin/users/{public_id}/activate` | `user_accounts.manage` | `{reason?}` | `200 UserDetail` |
| POST | `/admin/users/{public_id}/suspend` | `user_accounts.manage` | `{reason?}` | `200 UserDetail` (sessions revoked) |
| POST | `/admin/users/{public_id}/disable` | `user_accounts.manage` | `{reason?}` | `200 UserDetail` (sessions revoked) |
| POST | `/admin/users/{public_id}/password-reset` | `user_accounts.manage` | `{temporary_password}` | `204` (forces change, revokes sessions) |
| GET | `/admin/users/{public_id}/sessions` | `user_accounts.view` | – | `200 [SessionOut]` (active sessions) |
| POST | `/admin/users/{public_id}/sessions/{session_id}/revoke` | `user_sessions.revoke` | – | `204` |
| POST | `/admin/users/{public_id}/sessions/revoke-all` | `user_sessions.revoke` | – | `200 {revoked: int}` |
| POST | `/admin/users/{public_id}/roles` | `user_roles.assign` (+ the role's own assign permission) | `{role}` | `200 UserDetail` |
| DELETE | `/admin/users/{public_id}/roles/{role_code}` | `user_roles.assign` (+ the role's own assign permission) | – | `200 UserDetail` |

Errors: `404 user_not_found` / `session_not_found` / `role_not_found` / `role_not_granted`; `409 login_id_taken` / `email_taken` / `conflict` / `role_already_granted` / `invalid_status_transition` / `password_required`; `422 invalid_login_id` / `password_policy`; `403 self_modification_forbidden` / `insufficient_privilege` / `role_not_assignable` / `privilege_escalation`.

```text
UserSummary { public_id, login_id, display_name, email | null, status, roles: [role_code],
              last_login_at | null, created_at }
UserDetail  = UserSummary + { password_must_change, status_changed_at, status_reason | null,
              activated_at | null, deactivated_at | null, password_changed_at | null,
              role_grants: [{role, granted_at}] }
SessionOut  { public_id, created_at, last_seen_at, idle_expires_at, absolute_expires_at,
              ip_address | null, user_agent | null }
```

No schema contains a password hash, session token or token hash.

## 5. Administration — access roles and permissions (`/api/v1/admin`)

| Method | Path | Permission | Success |
|---|---|---|---|
| GET | `/admin/access-roles` | `access_roles.view` | `200 [AccessRoleOut]` |
| GET | `/admin/access-permissions` | `access_roles.view` | `200 [{code, description, is_privileged}]` |
| PUT | `/admin/access-roles/{role_code}/permissions/{permission_code}` | `access_roles.manage` | `200 AccessRoleOut` |
| DELETE | `/admin/access-roles/{role_code}/permissions/{permission_code}` | `access_roles.manage` | `200 AccessRoleOut` |

Errors: `404 role_not_found` / `permission_not_found` / `permission_not_granted`; `409 permission_already_granted`; `403 role_not_editable` (Super Admin role) / `privileged_permission` (privileged codes only on Super Admin).

```text
AccessRoleOut { code, name, description, is_system, is_api_assignable,
                assign_permission: permission_code | null, permissions: [permission_code] }
```

## 6. Administration — audit log (`/api/v1/admin/audit-events`)

| Method | Path | Permission | Query | Success |
|---|---|---|---|---|
| GET | `/admin/audit-events` | `audit.view` | `event_type?`, `outcome?` (`success` \| `failure` \| `denied`), `actor?` (public_id), `target_type?`, `target_id?`, `occurred_from?` (inclusive), `occurred_to?` (exclusive), `limit` 1–200 (default 50), `cursor?` | `200 Page[AuditEventOut]` |

**Every call is itself recorded** as `audit.events.viewed` (with the filters used). There are no update or delete endpoints.

```text
AuditEventOut { event_id, occurred_at, event_type, outcome,
                actor: {public_id, login_id, display_name} | null,
                target_type | null, target_id | null, request_id | null,
                source_ip | null, user_agent | null, metadata: object | null }
```

Event types: `auth.login.succeeded`, `auth.login.failed`, `auth.login.throttled`, `auth.login.denied_inactive`, `auth.logout`, `auth.password.changed`, `auth.password.change_failed`, `user_account.created`, `user_account.updated`, `user_account.activated`, `user_account.suspended`, `user_account.disabled`, `user_account.password_reset`, `user_session.revoked`, `user_session.revoked_all`, `access_role.granted`, `access_role.revoked`, `access_role.permission_granted`, `access_role.permission_revoked`, `super_admin.bootstrapped`, `super_admin.granted`, `super_admin.revoked`, `authorization.denied`, `audit.events.viewed`.

## 7. Not exposed over HTTP

Super Admin creation, grant and revocation exist only as CLI commands (`python -m app.cli …`, ADR-047). Kiosk PIN sign-in, badge tokens, organisation-scoped role assignment and certificate verification are not implemented (Q-08, Q-09; Stages C and J).
