# LMS API Reference (Stages B, C1, C3 and D)

| | |
|---|---|
| **Status** | Implemented. Every endpoint below exists in `LMS_Backend/app/api/routes/`. This list is checked against the routes registered by `create_app()`. |
| **Base path** | `/api/v1` (served on the same origin as the SPA; ADR-011) |
| **Machine-readable** | `GET /api/v1/openapi.json` and Swagger UI at `/api/docs` — development only (disabled in production) |
| **Related** | [System architecture §7, §11](LMS_SYSTEM_ARCHITECTURE.md) · [Organisation architecture](ORGANISATION_ARCHITECTURE.md) · [Decisions ADR-040…053](../decisions/ARCHITECTURAL_DECISIONS.md) · [Database design §4–5](../database/LMS_DATABASE_DESIGN.md) |

## 1. Conventions

| Topic | Rule |
|---|---|
| Format | JSON, UTF-8, `snake_case` fields; timestamps ISO 8601 UTC. |
| Identifiers | Resources are addressed by `public_id` (UUIDv7) — never by internal numeric keys (ADR-049). |
| Session | HttpOnly cookie `lms_session` (`__Host-lms_session` when Secure), set by sign-in and password change. Browsers send it automatically; the token is never in a response body (ADR-043). |
| CSRF | **Every** POST/PUT/PATCH/DELETE needs an `Origin` (or `Referer`) listed in `LMS_TRUSTED_ORIGINS`, otherwise `403 origin_not_allowed`. Authenticated state-changing requests also need `X-CSRF-Token: <csrf_token>`, otherwise `403 csrf_failed`. Sign-in needs no token (ADR-044). |
| Authorisation | Deny by default. Each non-public route requires a session and, for administration, organisation and employee data, a permission code. Missing permission → `403 forbidden` (audited as `authorization.denied`). Accounts that must change their password get `403 password_change_required` on permission-guarded routes. |
| Pagination | `limit` + opaque `cursor`; responses are `{"items": [...], "next_cursor": "…" \| null}` — newest first for administration lists, by `code` for organisation lists and by `employee_code` for employee lists. Pass `next_cursor` back as `cursor`. A malformed cursor → `422 invalid_cursor`. Small organisation catalogues (unit types, locations, job families, grades, levels) are returned as plain arrays. |
| Versions | Records that can be changed carry `version`. Every change request sends the `version` it last read; a stale value → `409 version_conflict` (reload and retry). |
| Dates | Business dates are `YYYY-MM-DD`. Effective periods are half-open `[effective_from, effective_to)`: `effective_to` is the first day on which a record no longer applies (user interfaces should label it accordingly, e.g. "Ends (exclusive)" or show the last day as `effective_to − 1`); `effective_from: null` means the start was not recorded. `as_of` defaults to today's business date (`LMS_BUSINESS_UTC_OFFSET_MINUTES`, default UTC+05:30). |
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
| GET | `/admin/users` | `user_accounts.view` | query `status?` (`pending_activation` \| `active` \| `suspended` \| `disabled`), `q?` (≤ 100; login ID or name contains), `linked?` (C3: `true` = linked to an employee, `false` = not linked), `manageable?` (C3b: `true` = only accounts the caller may manage — not their own, no permission the caller lacks; the same rule as every change, used by the employee account picker), `limit` 1–100 (default 25), `cursor?` | `200 Page[UserSummary]` |
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

Errors: `404 user_not_found` / `session_not_found` / `role_not_found` / `role_not_granted`; `409 login_id_taken` / `email_taken` / `conflict` / `role_already_granted` / `invalid_status_transition` / `password_required` / `employee_has_active_account` (C3: re-activating a disabled account while the same employee has another account that is not disabled); `422 invalid_login_id` / `password_policy`; `403 self_modification_forbidden` / `insufficient_privilege` / `role_not_assignable` / `privilege_escalation`.

```text
UserSummary { public_id, login_id, display_name, email | null, status, roles: [role_code],
              last_login_at | null, created_at,
              employee: {public_id, employee_code, full_name} | null }   (C3: linked employee; null unless the caller also holds employees.view)
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

## 7. Organisation structure (`/api/v1/org`)

Reads require `organisation.view` (Supervisor, HOD, SME, HR Admin, Super Admin); changes require `organisation.manage` (HR Admin, Super Admin). Every change is audited. Organisational units grant **no** permissions. Nothing is deleted: units are closed, catalogue entries deactivated.

| Method | Path | Permission | Request | Success |
|---|---|---|---|---|
| GET | `/org/unit-types` | `organisation.view` | – | `200 [OrgUnitTypeOut]` (by `sort_order`, `code`) |
| POST | `/org/unit-types` | `organisation.manage` | `{code, name, description?, sort_order?, allows_employee_assignment?, parent_rule_mode? (advisory \| strict), translations?}` | `201 OrgUnitTypeOut` |
| GET | `/org/unit-types/{public_id}` | `organisation.view` | – | `200 OrgUnitTypeOut` |
| PATCH | `/org/unit-types/{public_id}` | `organisation.manage` | `{version, name?, description?, sort_order?, allows_employee_assignment?, is_active?, parent_rule_mode?, translations?}` (the code is fixed) | `200 OrgUnitTypeOut` |
| PUT | `/org/unit-types/{public_id}/parent-rules` | `organisation.manage` | `{version, allow_root, parent_type_ids: [public_id]}` — replaces the rules; empty with `allow_root: false` means no rules | `200 OrgUnitTypeOut` |
| GET | `/org/units` | `organisation.view` | query `as_of?`, `q?` (code or name contains), `unit_type?`, `parent?` (direct children), `roots_only?`, `include_closed?`, `limit` 1–200 (default 50), `cursor?` | `200 Page[OrgUnitOut]` |
| POST | `/org/units` | `organisation.manage` | `{code, name, short_name?, unit_type_id, location_id?, parent_id? (null = root), effective_from?, external_ref?, translations?}` | `201 OrgUnitWriteOut` |
| GET | `/org/tree` | `organisation.view` | query `as_of?`, `include_closed?` | `200 OrgTreeOut` (flat node list; build the tree from `parent_id`) |
| GET | `/org/units/{public_id}` | `organisation.view` | query `as_of?` | `200 OrgUnitOut` |
| PATCH | `/org/units/{public_id}` | `organisation.manage` | **Correction** of wrongly recorded data: `{version, reason?, code?, name?, short_name?, unit_type_id?, location_id?, effective_from?, external_ref?, translations?}` | `200 OrgUnitWriteOut` |
| POST | `/org/units/{public_id}/move` | `organisation.manage` | **Reorganisation**: `{version, new_parent_id (null = root), effective_date}` — ends the current placement and opens a new one | `200 OrgUnitWriteOut` (shown as of `effective_date`) |
| POST | `/org/units/{public_id}/close` | `organisation.manage` | `{version, effective_date, reason?}` | `200 OrgUnitWriteOut` |
| POST | `/org/units/{public_id}/reopen` | `organisation.manage` | `{version, reason?}` — undoes a closure | `200 OrgUnitWriteOut` |
| GET | `/org/units/{public_id}/history` | `organisation.view` | – | `200 UnitHistoryOut` (all placements, oldest first) |
| GET | `/org/locations` | `organisation.view` | query `include_inactive?` | `200 [LocationOut]` |
| POST | `/org/locations` | `organisation.manage` | `{code, name, address_line1?, address_line2?, city?, state?, postal_code?, country_code? (2 letters), time_zone? (IANA name)}` | `201 LocationOut` |
| GET | `/org/locations/{public_id}` | `organisation.view` | – | `200 LocationOut` |
| PATCH | `/org/locations/{public_id}` | `organisation.manage` | `{version, any create field, is_active?}` | `200 LocationOut` |

Structure rules:

* **Codes** are upper-cased, `[A-Z0-9][A-Z0-9_-]{0,49}`, and unique per catalogue (case-insensitive). **Names** are unique only among siblings (same parent, overlapping dates): two plants may each have a "Maintenance" department.
* A parent must exist for the whole period of a placement; a unit has at most one parent on any date; cycles are refused. Parent-type rules either warn (`advisory`: returned in `warnings` and recorded in the audit event) or reject (`strict`).
* Hierarchy changes are serialised by a database lock, so concurrent moves cannot together create a cycle.
* **Closing** is refused while the unit has active children, active functional roles it owns, or open designation mappings scoped to it; `details` lists each blocker (`active_child`, `owned_functional_role`, `scoped_mapping`, and from C3 `employee_assignment` / `employee_responsibility` for employee records in the unit that continue after the closure date). Correcting a unit's start date to later than an employee assignment or responsibility in it is refused (`422 period_conflict`).

Errors: `404 unit_type_not_found` / `org_unit_not_found` / `location_not_found`; `409 unit_type_code_taken` / `unit_code_taken` / `location_code_taken` / `sibling_name_taken` / `later_change_exists` / `unit_has_dependants` / `unit_already_closed` / `unit_not_closed` / `parent_closed` / `location_in_use` / `version_conflict`; `422 invalid_code` / `invalid_period` / `parent_not_active` / `type_rule_violation` / `hierarchy_cycle` / `move_date_invalid` / `no_change` / `period_conflict` / `unit_type_inactive` / `location_inactive` / `invalid_time_zone`.

```text
RefOut          { public_id, code, name }
OrgUnitTypeOut  { public_id, code, name, description | null, sort_order, allows_employee_assignment,
                  is_active, parent_rule_mode, allow_root, allowed_parent_types: [RefOut],
                  translations: {bn?, hi?, gu?}, version, created_at, updated_at }
OrgUnitOut      { public_id, code, name, short_name | null, unit_type: RefOut, location: RefOut | null,
                  as_of, parent: RefOut | null, path: [RefOut] (root to parent),
                  status: active | closed | not_started, effective_from | null, effective_to | null,
                  external_ref | null, translations, version, created_at, updated_at }
OrgUnitWriteOut { unit: OrgUnitOut, warnings: [{code, message}] }
OrgTreeOut      { as_of, nodes: [{public_id, code, name, short_name, unit_type, location,
                  parent_id | null, status, translations}] }
UnitHistoryOut  { unit: RefOut, effective_from, effective_to,
                  placements: [{parent: RefOut, effective_from, effective_to, recorded_at, ended_at}] }
LocationOut     { public_id, code, name, address_line1, address_line2, city, state, postal_code,
                  country_code, time_zone, is_active, version, created_at, updated_at }
```

`translations` holds display names for `bn`, `hi` and `gu`; the stored name (English or as supplied) is canonical. In requests, an empty or null value removes a locale; any other locale is rejected (`422`).

## 8. Occupational reference data (`/api/v1/org`)

Reads require `organisation.view`. None of these records grant LMS permissions, and responsibilities never establish practical authorisation. Grades and levels are two **independent** optional lists (Q-45). Functional roles are neither organisational sub-functions nor access roles.

| Method | Path | Permission | Request | Success |
|---|---|---|---|---|
| GET | `/org/job-families` | `organisation.view` | query `include_inactive?` | `200 [JobFamilyOut]` |
| POST | `/org/job-families` | `designations.manage` | `{code, name, description?, parent_id?}` | `201 JobFamilyOut` |
| GET | `/org/job-families/{public_id}` | `organisation.view` | – | `200 JobFamilyOut` |
| PATCH | `/org/job-families/{public_id}` | `designations.manage` | `{version, code?, name?, description?, parent_id?, is_active?}` | `200 JobFamilyOut` |
| GET | `/org/grades` | `organisation.view` | query `include_inactive?` | `200 [RankedOut]` (by `rank`, unranked last) |
| POST | `/org/grades` | `designations.manage` | `{code, name, rank?}` | `201 RankedOut` |
| GET | `/org/grades/{public_id}` | `organisation.view` | – | `200 RankedOut` |
| PATCH | `/org/grades/{public_id}` | `designations.manage` | `{version, code?, name?, rank?, is_active?}` | `200 RankedOut` |
| GET | `/org/levels` | `organisation.view` | query `include_inactive?` | `200 [RankedOut]` |
| POST | `/org/levels` | `designations.manage` | `{code, name, rank?}` | `201 RankedOut` |
| GET | `/org/levels/{public_id}` | `organisation.view` | – | `200 RankedOut` |
| PATCH | `/org/levels/{public_id}` | `designations.manage` | `{version, code?, name?, rank?, is_active?}` | `200 RankedOut` |
| GET | `/org/designations` | `organisation.view` | query `q?`, `include_inactive?`, `limit` 1–200 (default 100), `cursor?` | `200 Page[DesignationOut]` |
| POST | `/org/designations` | `designations.manage` | `{code, title, job_family_id?, translations?}` | `201 DesignationOut` |
| GET | `/org/designations/{public_id}` | `organisation.view` | – | `200 DesignationOut` |
| PATCH | `/org/designations/{public_id}` | `designations.manage` | `{version, code?, title?, job_family_id?, is_active?, translations?}` | `200 DesignationOut` |
| GET | `/org/designations/{public_id}/functional-roles` | `organisation.view` | query `include_ended?` | `200 [DesignationRoleMappingOut]` |
| POST | `/org/designations/{public_id}/functional-roles` | `functional_roles.manage` | `{functional_role_id, scope_unit_id? (null = everywhere), include_descendants? (default true), effective_from? (default today)}` | `201 DesignationRoleMappingOut` |
| POST | `/org/designations/{public_id}/functional-roles/{mapping_id}/end` | `functional_roles.manage` | `{effective_to, reason?}` | `200 DesignationRoleMappingOut` |
| GET | `/org/functional-roles` | `organisation.view` | query `q?`, `include_inactive?`, `owner_unit?`, `limit` 1–200 (default 100), `cursor?` | `200 Page[FunctionalRoleOut]` |
| POST | `/org/functional-roles` | `functional_roles.manage` | `{code, name, description?, job_family_id?, owner_unit_id?, translations?}` | `201 FunctionalRoleOut` |
| GET | `/org/functional-roles/{public_id}` | `organisation.view` | – | `200 FunctionalRoleOut` |
| PATCH | `/org/functional-roles/{public_id}` | `functional_roles.manage` | `{version, code?, name?, description?, job_family_id?, owner_unit_id?, is_active?, translations?}` | `200 FunctionalRoleOut` |
| GET | `/org/responsibilities` | `organisation.view` | query `q?`, `include_inactive?`, `limit` 1–200 (default 100), `cursor?` | `200 Page[ResponsibilityOut]` |
| POST | `/org/responsibilities` | `responsibilities.manage` | `{code, name, description?, category?, translations?}` | `201 ResponsibilityOut` |
| GET | `/org/responsibilities/{public_id}` | `organisation.view` | – | `200 ResponsibilityOut` |
| PATCH | `/org/responsibilities/{public_id}` | `responsibilities.manage` | `{version, code?, name?, description?, category?, is_active?, translations?}` | `200 ResponsibilityOut` |

Mapping rules: a designation may map to many roles, and a role may come from many designations. The same designation, role and scope cannot have overlapping periods (`409 mapping_overlap`). A scoped mapping applies to the scope unit and, by default, its descendants. Employees' derived functional roles are computed from these mappings (§10).

Errors: `404 job_family_not_found` / `grade_not_found` / `job_level_not_found` / `designation_not_found` / `functional_role_not_found` / `responsibility_not_found` / `mapping_not_found`; `409 <kind>_code_taken` / `designation_in_use` / `functional_role_in_use` / `mapping_overlap` / `mapping_already_ended` / `version_conflict`; `422 invalid_code` / `job_family_cycle` / `job_family_inactive` / `designation_inactive` / `functional_role_inactive` / `unit_closed` / `unit_not_active` / `invalid_period`.

```text
JobFamilyOut      { public_id, code, name, description, parent: RefOut | null, is_active, version, created_at, updated_at }
RankedOut         { public_id, code, name, rank | null, is_active, version, created_at, updated_at }   (grade or level)
DesignationOut    { public_id, code, title, job_family: RefOut | null, is_active, translations, version, created_at, updated_at }
FunctionalRoleOut { public_id, code, name, description, job_family, owner_unit: RefOut | null,
                    is_active, translations, version, created_at, updated_at }
DesignationRoleMappingOut { public_id, designation: RefOut, functional_role: RefOut,
                    scope_unit: RefOut | null, include_descendants, effective_from, effective_to,
                    created_at, ended_at }
ResponsibilityOut { public_id, code, name, description, category, is_active, translations, version, created_at, updated_at }
```

Audit event types added in C1: `org_unit_type.created`, `org_unit_type.updated`, `org_unit_type.parent_rules_changed`, `org_unit.created`, `org_unit.corrected`, `org_unit.moved`, `org_unit.closed`, `org_unit.reopened`, `location.created`, `location.updated`, `job_family.created`, `job_family.updated`, `grade.created`, `grade.updated`, `job_level.created`, `job_level.updated`, `designation.created`, `designation.updated`, `functional_role.created`, `functional_role.updated`, `designation_role_mapping.created`, `designation_role_mapping.ended`, `responsibility.created`, `responsibility.updated`.

## 9. Employees (`/api/v1/employees`) — Stage C3

Employee records are **separate from login accounts** (ADR-040): an employee may have no account, and an account may have no employee. Interim permissions (Q-51; global only — scoped access is Stage C4): `employees.view`, `employees.history.view`, `employees.manage` and `reporting_lines.manage`, all held by HR Admin and Super Admin only. Account linking needs **both** `employees.manage` and `user_accounts.manage`. Being a manager in a reporting line grants **no** role and no data access. Every change is audited with target type `employee` (the employee's `public_id`), so an employee's history is a single query.

| Method | Path | Permission | Request | Success |
|---|---|---|---|---|
| GET | `/employees` | `employees.view` | query `as_of?`, `q?` (code or name contains), `status?` (`active` \| `on_leave` \| `separated` \| `unknown`), `unit?` + `include_descendants?`, `location?`, `designation?`, `has_account?`, `limit` 1–200 (default 50), `cursor?` | `200 Page[EmployeeSummary]` (by `employee_code`) |
| POST | `/employees` | `employees.manage` | `{employee_code, full_name, display_name?, preferred_language? (en \| bn \| hi \| gu), work_email?, employment_status? (null = not recorded), date_of_joining?, date_of_separation? (separated only), external_ref?}` | `201 EmployeeOut` |
| GET | `/employees/reporting-types` | `employees.view` | – | `200 [ReportingTypeOut]` (C3 seeds only `LINE_MANAGER`) |
| GET | `/employees/data-quality` | `employees.manage` | query `as_of?`, `check?`, `limit` 1–200, `cursor?` | `200 DataQualityOut` (counts for every check; the employees failing `check`) |
| GET | `/employees/{public_id}` | `employees.view` | query `as_of?` | `200 EmployeeOut` |
| PATCH | `/employees/{public_id}` | `employees.manage` | **Correction**: `{version, reason?, employee_code?, full_name?, display_name?, preferred_language?, work_email?, date_of_joining?, external_ref?}` | `200 EmployeeOut` |
| POST | `/employees/{public_id}/employment-status` | `employees.manage` | `{version, status (active \| on_leave \| separated), separation_date? (last working day; required for separated), end_open_records? (default false), end_direct_reports? (default false), reason?}` | `200 EmployeeOut` |
| GET | `/employees/{public_id}/separation-preview` | `employees.manage` | query `separation_date` (required; the last working day, sent unchanged) | `200 SeparationPreviewOut`. **Read-only**: nothing is written or audited. The separation itself re-checks everything under locks, so a preview can become stale and the POST may still return `409` |
| GET | `/employees/{public_id}/history` | `employees.history.view` | query `limit` 1–100 (default 50), `cursor?` | `200 Page[AuditEventOut]` (newest first; `source_ip` and `user_agent` are omitted — they remain in the audit log under `audit.view`) |
| GET | `/employees/{public_id}/assignments` | `employees.history.view` | query `include_ended?` (default true) | `200 [AssignmentOut]` (timeline) |
| POST | `/employees/{public_id}/assignments` | `employees.manage` | `{assignment_type? (primary \| additional \| acting \| deputation; default primary), org_unit_id, designation_id?, grade_id?, job_level_id?, location_id?, effective_from?, effective_to?, reason?}` | `201 AssignmentWriteOut` |
| POST | `/employees/{public_id}/assignments/{assignment_id}/change` | `employees.manage` | **Business change from a date** (transfer, designation, grade, level or location): `{version, effective_date, org_unit_id?, designation_id?, grade_id?, job_level_id?, location_id?, reason?}` — closes the row at `effective_date` and opens an updated copy | `201 AssignmentWriteOut` (the new row) |
| POST | `/employees/{public_id}/assignments/{assignment_id}/end` | `employees.manage` | `{version, effective_to, reason?}` | `200 AssignmentOut` |
| PATCH | `/employees/{public_id}/assignments/{assignment_id}` | `employees.manage` | **Correction** (the explicit mechanism for back-dated fixes): `{version, reason?, assignment_type?, org_unit_id?, designation_id?, grade_id?, job_level_id?, location_id?, effective_from?, effective_to?}` | `200 AssignmentWriteOut` |
| GET | `/employees/{public_id}/functional-roles` | `employees.view` | query `as_of?`, `include_ended?` | `200 FunctionalRolesOut` |
| POST | `/employees/{public_id}/functional-roles` | `employees.manage` | `{functional_role_id, kind? (manual \| exclusion; default manual), effective_from?, effective_to?, reason?}` | `201 RoleRecordOut` |
| POST | `/employees/{public_id}/functional-roles/{record_id}/end` | `employees.manage` | `{effective_to, reason?}` | `200 RoleRecordOut` |
| GET | `/employees/{public_id}/responsibilities` | `employees.view` | query `include_ended?` | `200 [ResponsibilityRecordOut]` |
| POST | `/employees/{public_id}/responsibilities` | `employees.manage` | `{responsibility_id, context_unit_id?, context_location_id?, effective_from?, effective_to?, reason?}` | `201 ResponsibilityRecordOut` |
| POST | `/employees/{public_id}/responsibilities/{record_id}/end` | `employees.manage` | `{effective_to, reason?}` | `200 ResponsibilityRecordOut` |
| GET | `/employees/{public_id}/reporting` | `employees.view` | query `as_of?` | `200 ReportingOut` (managers on `as_of`, full history, direct reports on `as_of`) |
| POST | `/employees/{public_id}/reporting` | `reporting_lines.manage` | `{manager_id, relationship_type_id? (default LINE_MANAGER), effective_from?, reason?}` — a new line manager closes the current one on `effective_from` | `201 ReportingRecordOut` |
| POST | `/employees/{public_id}/reporting/{record_id}/end` | `reporting_lines.manage` | `{effective_to, reason?}` | `200 ReportingRecordOut` |
| GET | `/employees/{public_id}/account` | `employees.view` | – | `200 EmployeeAccountOut` |
| PUT | `/employees/{public_id}/account` | `employees.manage` + `user_accounts.manage` | `{user_public_id, reason?}` | `200 EmployeeAccountOut` |
| POST | `/employees/{public_id}/account/unlink` | `employees.manage` + `user_accounts.manage` | `{user_public_id, reason?}` — removes the link only; the account is unchanged | `200 EmployeeAccountOut` |

Employee rules:

* **Employee code**: mandatory, at most 30 characters, trimmed and stored in capitals; letters, digits, `/`, `.`, `_`, `-` (Q-54). Always text — leading zeros are kept (`00123` and `123` are different codes). Unique ignoring case.
* **Employment status** is `active`, `on_leave`, `separated` or **null = not recorded**. An unknown status is never treated as active: the directory filter `status=unknown` and the data-quality check `unknown_status` show it explicitly. The history of status changes is kept in the audit trail (Q-56).
* **Separation**: `date_of_separation` is the employee's **last working day**. Because periods are half-open, records ended by separation get `effective_to` = the **following day** (the first day they no longer apply): separation on 30 June ends records with `effective_to: 1 July`. Separation ends nothing silently. It is refused (`409 open_records_on_separation`) while records continue after the separation date, and `details` lists every one (`location` = `[kind, code]`):
  * the employee's own records — `open_assignment`, `open_functional_role`, `open_responsibility`, `open_reporting_line` (the employee as subordinate; code = manager). `end_open_records: true` ends them in the same transaction;
  * reporting lines of the employee's **direct reports** (the employee as manager) — `open_direct_report` (code = the subordinate). These belong to other employees, so they need their own explicit confirmation, `end_direct_reports: true`. Each one ended this way is also audited on the subordinate (`reporting_relationship.ended` with `cause: manager_separated`);
  * `starts_after_separation` — a record starting after the last working day, which cannot be ended this way and must be corrected or ended first.

  Rows ended by separation record the acting administrator (`ended_by`, and `updated_by` on assignments) in the same transaction, and the `employee.status_changed` event lists them under `ended_records`. Separation **never** changes the linked LMS account (Q-50).
* **Concurrency and lock order**: every write to reporting lines (set or end a manager) and every separation first takes the reporting graph lock, then locks the employee rows involved in ascending internal order, then reads dependent rows with locking reads. Concurrent operations on the same employees therefore wait for each other instead of deadlocking, and the one that runs second sees the first one's committed result (for example, a new direct report added while the manager is being separated is listed as a blocker, and a manager separated first cannot receive a new report: `422 manager_separated`).
* **Assignments**: half-open periods; at most one primary on any date; no overlapping assignments to the same unit; additional, acting and deputation assignments may overlap the primary. The unit must exist for the whole new period, and newly chosen designation, grade, level and location must be active. Records must fall inside known employment dates (a start date is required once the joining date is known). Assigning to a unit type with `allows_employee_assignment = false` only warns (`unit_type_not_assignable`, Q-55). History is never overwritten: business changes close and reopen rows; corrections are audited before and after.
* **Organisation context** (`primary_unit`, `path`) is derived as of the requested date from the hierarchy, so a later reorganisation does not rewrite where an employee sat.
* **Functional roles** on a date = roles derived from **every** assignment covering it (through designation → role mappings, honouring scope and descendants) + manual roles − exclusions. Derived roles are computed, never stored; an excluded role is listed with `effective: false`. Functional roles grant no permissions.
* **Responsibilities** may carry a unit and/or location context; the same responsibility in the same context cannot overlap. Nothing is seeded, and responsibilities grant no permission or practical authorisation.
* **Reporting lines**: no self-reporting, no cycles (serialised by a database lock), at most one line manager on any date, and the manager must not be separated. Only `LINE_MANAGER` is seeded (Q-52).
* **Account links**: at most one non-disabled linked account per employee (enforced by the database); disabled accounts keep their link as history. The Stage B guards apply (no self-linking; no linking accounts holding permissions the actor lacks). The employee code is never forced as the login ID (Q-50). `flags` lists mismatches for review: `separated_with_active_account`, `email_mismatch`.
* **Data-quality checks** (report only; nothing is corrected): `unknown_status`, `no_primary_assignment`, `missing_location` (neither the assignment nor its unit has one), `missing_designation`, `separated_with_active_account`, `manager_inactive` (line manager separated or on leave), `no_line_manager`, `incomplete_record` (joining date not recorded). Employees with unknown status are included wherever current employees are checked.

Errors: `404 employee_not_found` / `assignment_not_found` / `role_assignment_not_found` / `responsibility_record_not_found` / `reporting_relationship_not_found` / `reporting_type_not_found` / `manager_not_found` / `user_not_found` / `org_unit_not_found` / `designation_not_found` / `grade_not_found` / `level_not_found` / `location_not_found` / `functional_role_not_found` / `responsibility_not_found`; `409 employee_code_taken` / `open_records_on_separation` / `primary_overlap` / `assignment_overlap` / `assignment_already_ended` / `record_already_ended` / `role_assignment_overlap` / `responsibility_overlap` / `manager_overlap` / `reporting_cycle` / `later_change_exists` / `account_already_linked` / `employee_has_active_account` / `account_not_linked` / `version_conflict`; `422 invalid_employee_code` / `invalid_employment_dates` / `separation_date_required` / `separation_date_not_allowed` / `outside_employment_period` / `assignment_start_required` / `unit_required` / `unit_not_active` / `reference_inactive` / `change_date_invalid` / `invalid_period` / `functional_role_inactive` / `responsibility_inactive` / `location_inactive` / `self_reporting` / `manager_separated` / `reporting_type_inactive` / `invalid_check` / `no_change`; `403 self_modification_forbidden` / `insufficient_privilege` (account links).

```text
EmployeeRef     { public_id, employee_code, full_name, employment_status | null }
EmployeeSummary { public_id, employee_code, full_name, display_name | null,
                  employment_status: active | on_leave | separated | null, as_of,
                  primary_unit: RefOut | null, path: [RefOut] (root to the unit's parent),
                  designation: RefOut | null, location: RefOut | null (assignment, else unit),
                  line_manager: EmployeeRef | null, has_active_account }
EmployeeOut     = EmployeeSummary + { preferred_language | null, work_email | null,
                  date_of_joining | null, date_of_separation | null, external_ref | null,
                  accounts: [AccountRef], version, created_at, updated_at }
AccountRef      { public_id, login_id, display_name, status }
AssignmentOut   { public_id, assignment_type, org_unit: RefOut, designation, grade, job_level,
                  location (each RefOut | null), effective_from | null, effective_to | null,
                  source, reason | null, version, created_at, updated_at }
AssignmentWriteOut { assignment: AssignmentOut, warnings: [{code, message}] }
FunctionalRolesOut { as_of, roles: [EffectiveRoleOut], records: [RoleRecordOut] }
EffectiveRoleOut   { functional_role: RefOut, effective,
                     derived_from: [{assignment, assignment_type, org_unit, designation, mapping}],
                     manual: RoleRecordOut | null, exclusion: RoleRecordOut | null }
RoleRecordOut      { public_id, functional_role: RefOut, kind: manual | exclusion,
                     effective_from, effective_to, reason, created_at }
ResponsibilityRecordOut { public_id, responsibility: RefOut, context_unit: RefOut | null,
                     context_location: RefOut | null, effective_from, effective_to, reason, created_at }
ReportingTypeOut   { public_id, code, name, allows_multiple, is_hierarchical, is_active, translations }
ReportingRecordOut { public_id, relationship_type: RefOut, employee: EmployeeRef, manager: EmployeeRef,
                     effective_from, effective_to, reason, created_at }
ReportingOut       { as_of, managers: [ReportingRecordOut], history: [...], direct_reports: [...] }
EmployeeAccountOut { accounts: [AccountRef] (including disabled), flags: [string],
                     history: [AuditEventOut] (link and unlink events, newest first;
                     no source_ip / user_agent) }
DataQualityOut     { as_of, counts: {check: int}, check | null, items: [EmployeeSummary], next_cursor }
SeparationPreviewOut { employee: EmployeeRef, version, separation_date (as requested),
                     records_end_on (= separation_date + 1 day; the effective_to ended records get),
                     own_records: [{record_id, kind: assignment | functional_role | responsibility
                       | reporting_line, code, name, effective_from, effective_to,
                       starts_after_separation}],
                     direct_reports: [{record_id, employee: EmployeeRef (the subordinate),
                       relationship_type: RefOut, effective_from, effective_to,
                       starts_after_separation}],
                     requires_end_open_records, requires_end_direct_reports, blocked }
```

No employee schema has compensation (CTC, salary), bank, government-identifier (Aadhaar, PAN), date-of-birth, gender, home-address, health, family or personal-contact fields; the LMS does not store them.

Audit event types added in C3: `employee.created`, `employee.corrected`, `employee.status_changed`, `employee_assignment.created`, `employee_assignment.changed`, `employee_assignment.ended`, `employee_assignment.corrected`, `employee_functional_role.assigned`, `employee_functional_role.excluded`, `employee_functional_role.ended`, `employee_responsibility.assigned`, `employee_responsibility.ended`, `reporting_relationship.created`, `reporting_relationship.ended`, `employee_account.linked`, `employee_account.unlinked`. Reads are not audited.

## 10. Excel imports — Import Control Room (`/api/v1/imports`) — Stage D

Controlled onboarding of workbook data through **versioned import profiles** ([Excel import profiles](../database/EXCEL_IMPORT_PROFILES.md)). Stage D implements one profile, `employees` v1 (employees, assignments and reporting lines). Nothing is written to business tables until an authorised user explicitly approves a validated preview, and the commit is one transaction.

Permissions (migration 0010; HR Admin and Super Admin only): `imports.view` for every route; `imports.<profile>.run` to upload, map, validate, decide rows and cancel; `imports.<profile>.commit` **plus the domain permissions the commit writes with** (`employees.manage` and `reporting_lines.manage` for `employees`) to commit — an import never allows more than the equivalent manual screens; `imports.mappings.manage` to decide reference mappings. Import jobs are a shared administrative workspace: any holder of these permissions may act on any job, and each action is attributed.

| Method | Path | Permission | Request | Response |
|---|---|---|---|---|
| GET | `/imports/profiles` | `imports.view` | – | `200 [ImportProfileOut]` (latest version of each profile, with `can_run` / `can_commit` for the caller) |
| GET | `/imports/profiles/{code}/template` | `imports.view` | – | `200` `.xlsx` attachment: an Instructions sheet and one sheet per section; code columns are formatted as text |
| POST | `/imports` | `imports.view` + `imports.<profile>.run` | query `profile`; **raw body** = the `.xlsx` file (`Content-Type` the OOXML spreadsheet type or `application/octet-stream`; not a form); header `X-File-Name` (percent-encoded display name) | `201 ImportJobOut` (`mapping_required`, with a suggested mapping). File checks fail with `413 file_too_large`, `415 file_type_not_allowed` or `422 file_*` / `sheet_*`; a rejected file creates no job (audited as `import.upload.rejected`) |
| GET | `/imports` | `imports.view` | query `status?`, `profile?`, `limit` 1–100 (default 25), `cursor?` | `200 Page[ImportJobSummary]` (newest first). First runs the storage housekeeping: overdue jobs are marked `expired`, abandoned validations return to `mapping_required`, released and orphan files are deleted |
| GET | `/imports/mappings` | `imports.view` | query `kind?` (`org_unit` \| `designation` \| `location` \| `grade` \| `job_level`), `status?` (`pending` \| `approved` \| `rejected` \| `superseded`), `limit` 1–100, `cursor?` | `200 Page[ValueMappingOut]` (newest first; pending items carry `suggestions`) |
| POST | `/imports/mappings/{public_id}/approve` | `imports.view` + `imports.mappings.manage` | `{version, target_public_id, reason?}` | `200 ValueMappingOut` |
| POST | `/imports/mappings/{public_id}/reject` | `imports.view` + `imports.mappings.manage` | `{version, reason?}` | `200 ValueMappingOut` |
| POST | `/imports/mappings/{public_id}/withdraw` | `imports.view` + `imports.mappings.manage` | `{version, reason?}` — an approved or rejected decision becomes `superseded` (kept as history) and the label returns to the queue | `200 ValueMappingOut` (the superseded record) |
| GET | `/imports/{public_id}` | `imports.view` | – | `200 ImportJobOut` (an open job past its expiry is marked `expired` when read; a job left in `validating` for 30 minutes returns to `mapping_required`) |
| PUT | `/imports/{public_id}/mapping` | `imports.view` + `imports.<profile>.run` | `{version, sections: [{section, sheet, header_row, columns: {"<1-based column>": "<field>"}}]}` — one worksheet may be mapped as several sections; `header_row` must be the row detected at upload (`SheetOut.header_row`), otherwise `422 import_mapping_header_row` | `200 ImportJobOut` (`mapping_confirmed: true`; staged results and row decisions of an earlier validation are discarded) |
| POST | `/imports/{public_id}/validate` | `imports.view` + `imports.<profile>.run` | `{version}` | `200 ImportJobOut` (`ready_for_approval` or `validation_failed`). **Dry run**: every row runs through the real domain rules inside a transaction that is rolled back. At most 6,000 rows per import (`422 import_too_many_rows`) |
| POST | `/imports/{public_id}/rows/{row_id}/decision` | `imports.view` + `imports.<profile>.run` | `{version, decision: skip \| distinct \| null, reason?}` — `skip` needs a reason; `distinct` confirms that a probable duplicate is a different person; `null` clears the decision | `200 ImportJobOut` (`validation_failed`: validate again before approval) |
| POST | `/imports/{public_id}/commit` | `imports.view` + `imports.<profile>.commit` + domain permissions | `{version, confirm: true, apply_updates? (default false)}` — the explicit approval; without `apply_updates`, rows that would correct existing employees are skipped | `200 ImportJobOut` (`completed`, `completed_with_skips` or `failed`) |
| POST | `/imports/{public_id}/cancel` | `imports.view` + `imports.<profile>.run` | `{version}` | `200 ImportJobOut` (`cancelled`; the stored file is released and deleted after the status is saved) |
| GET | `/imports/{public_id}/rows` | `imports.view` | query `section?`, `outcome?` (`new` \| `update` \| `unchanged` \| `error` \| `skipped`), `limit` 1–200 (default 50), `cursor?` | `200 Page[RowOut]` (file order) |
| GET | `/imports/{public_id}/issues` | `imports.view` | query `severity?` (`error` \| `warning`), `code?`, `limit` 1–200, `cursor?` | `200 Page[IssueOut]` |
| GET | `/imports/{public_id}/error-report` | `imports.view` | – | `200` `.xlsx` attachment listing every issue (text cells only; values starting with `=`, `+`, `-`, `@`, tab or carriage return are prefixed with `'`) |

* **Lifecycle**: upload → `mapping_required` (until a mapping is confirmed) → `validating` → `validation_failed` \| `ready_for_approval` → `committing` → `completed` \| `completed_with_skips` \| `failed`. `cancelled` and `expired` (default 7 days after upload) close an open job; every state-changing action refuses an overdue job (`409 import_job_expired`) even before it is marked. Terminal jobs are read-only. Their stored file is released (`file_stored: false`) in the same transaction as the final status and deleted after it commits; a deletion that fails is retried by the housekeeping in `GET /imports`. Staged rows, issues, decisions and the audit trail are kept.
* **Approval rules**: commit needs status `ready_for_approval`, a validation no older than the preview validity (default 24 hours; `409 import_preview_expired`) and no reference-mapping decision made since validation (`409 import_revalidation_required`). The commit re-checks every row against current data under the `imports` lock, in one transaction: if any row now breaks a rule, nothing is written and the job becomes `failed`; if any row would now do something other than the approved preview (for example an employee created since validation), nothing is written, the job stays `ready_for_approval` and must be validated again (`409 import_records_changed`). Two simultaneous commits of one job create the records once (the second gets `409 import_not_ready` or `version_conflict`).
* **Idempotency and provenance**: rows are matched on their natural keys (employee code; employee + unit + assignment type + start date; employee + start date for reporting lines). Re-importing the same data reports the rows as `unchanged` and writes nothing. Every record created, updated or confirmed by an import has a `record_provenance` row (job and staged row, hence sheet, row number and file hash); `RowOut.target_public_id` is the record a row created or matched. `previously_imported_by` lists earlier jobs with the same file hash (a warning, not a refusal).
* **Reference values** (units, designations, locations, grades, levels) are matched by code, exact unique name or an **approved** mapping. Anything else becomes a pending mapping in the review queue with ranked suggestions; suggestions are never applied automatically, and an import never creates units, designations or other reference data.
* **Excluded data**: columns whose headers name compensation, bank, government-identifier, date-of-birth, gender, address, health, family or personal-contact data are excluded and cannot be mapped (`422 import_mapping_column_excluded`); their values never reach staging, issues, jobs, audit events, logs or reports.

Errors: `404 import_job_not_found` / `import_profile_not_found` / `import_row_not_found` / `import_mapping_not_found`; `409 import_invalid_transition` / `import_profile_unavailable` / `import_mapping_not_confirmed` / `import_not_ready` / `import_job_expired` / `import_preview_expired` / `import_revalidation_required` / `import_records_changed` / `import_mapping_already_decided` / `import_mapping_not_decided` / `import_file_unavailable` / `version_conflict`; `413 file_too_large`; `415 file_type_not_allowed`; `503 import_storage_unavailable` (the upload could not be stored); `422 file_extension_not_allowed` / `file_empty` / `file_encrypted_or_legacy` / `file_not_xlsx` / `file_corrupted` / `file_macro_enabled` / `file_unsafe_entry` / `file_expansion_limit` / `file_too_complex` / `file_too_many_sheets` / `sheet_too_many_rows` / `sheet_too_many_columns` / `import_too_many_rows` (at validation) / `import_mapping_empty` / `import_mapping_unknown_section` / `import_mapping_unknown_sheet` / `import_mapping_duplicate_section` / `import_mapping_header_row` / `import_mapping_unknown_field` / `import_mapping_field_twice` / `import_mapping_unknown_column` / `import_mapping_column_excluded` / `import_mapping_required_missing` / `import_decision_invalid` / `import_skip_reason_required` / `import_mapping_target_not_found` / `import_mapping_target_inactive`. Row-level problems are not HTTP errors: they are `IssueOut` records (codes listed in [Excel import profiles](../database/EXCEL_IMPORT_PROFILES.md)).

```text
ImportProfileOut { code, version, commit_mode, can_run, can_commit,
                   sections: [{kind, sheet_aliases, natural_key,
                               fields: [{name, type, required, aliases, reference | null}]}] }
ImportJobSummary { public_id, profile_code, profile_version, status, original_filename, file_size,
                   uploaded_by: AuditActorOut | null, uploaded_at, validated_at, committed_at,
                   finished_at, counts: {rows, blocking_errors, error_rows, warnings,
                   undecided_duplicates, importable, skipped_rows, skipped_blank,
                   skipped_repeated_header, by_section, committed} (keys present once known) }
ImportJobOut     = ImportJobSummary + { file_sha256, file_stored, version, failure_code | null,
                   workbook: [SheetOut], column_mapping: [{section, sheet, header_row, columns}],
                   mapping_confirmed, previously_imported_by: [uuid],
                   validated_by, committed_by (AuditActorOut | null) }
SheetOut         { name, state, dimensions | null, suggested_section | null, header_row | null,
                   headers: [{column, index, text, excluded, suggested_field | null}] }
RowOut           { id, section, sheet, row_number, outcome, values, source, changes | null,
                   decision | null, decision_reason | null, target_public_id | null,
                   issues: [IssueOut] }
IssueOut         { id, section, sheet, row_number, column, field, code,
                   severity: error | warning, source_value | null, params | null }
ValueMappingOut  { public_id, kind, source_text, normalised_text, status, target: RefOut | null,
                   decision_reason, decided_by, decided_at, created_at, version,
                   suggestions: [{public_id, code, label, score, reason}] }
```

Workbook cell values appear only in a job's staged rows and issues (mapped columns only); audit metadata records counts, codes and file hashes, never cell values. Audit event types added in Stage D (target type `import_job` or `import_value_mapping`): `import.job.uploaded`, `import.upload.rejected`, `import.job.mapping_set`, `import.job.validated`, `import.row.decided`, `import.job.committed`, `import.job.commit_failed`, `import.job.cancelled`, `import.job.expired`, `import.job.validation_abandoned`, `import.mapping.approved`, `import.mapping.rejected`, `import.mapping.superseded`. Records written by a commit are also audited with their usual C3 event types (for example `employee.created`) under the same request ID; corrections, assignments and reporting lines carry the import job and source row as their reason.

## 11. Not exposed over HTTP

Super Admin creation, grant and revocation exist only as CLI commands (`python -m app.cli …`, ADR-047). Kiosk PIN sign-in, badge tokens and certificate verification (Q-08, Q-09; Stage J), and organisation- and reporting-line-scoped access (Stage C4) are not implemented. Import profiles 2–6 (skill matrices, development plans, training calendars, safety calendars, attendance and historical training records) belong to later stages; the Stage D framework accepts new profiles without API changes.
