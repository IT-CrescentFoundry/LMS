# Migration 0011 — Execution Report (development database)

| | |
|---|---|
| **Date** | 2026-11-23 (upgrade run 20:45:29 – 20:45:35 IST) |
| **Target** | `crescent_lms_dev` on `127.0.0.1:3306`, MySQL 8.0.46 Community |
| **Revision** | `0010` → **`0011` (head)** |
| **Result** | **Applied and verified.** All pre-migration safety gates passed; all post-migration checks matched the approval package. |
| **Approval** | Explicit written approval of the database owner, 2026-11-23, conditional on every safety gate passing |
| **Procedure** | [`MIGRATION_0011_APPROVAL_PACKAGE.md`](../MIGRATION_0011_APPROVAL_PACKAGE.md) §4.2, §4.3, §6.2, §6.3 (the package itself was not edited) |

## 1. Purpose and scope

Migration `0011` adds the first-release schema: training register, competency library,
skill matrices and in-app notifications. It seeds six permissions with 12 role grants and two
proficiency scales with nine levels. This task covered only executing and verifying the migration.
No organisation, employee, competency, training or calendar data was imported. No
application feature, RBAC rule, MySQL account or scheduler was changed.

## 2. Repository reference

| Item | Value |
|---|---|
| Repository | `CF Projects\LMS` |
| Branch | `master` (tracking `origin/master`, not ahead/behind) |
| Commit | `08758af32e414a0f9d17fe98a5d26e66cd79da63` ("Organization Data Import and Database Management") |
| Working tree | Uncommitted first-release work present (modified and untracked files). It was preserved as found: nothing was reset, stashed, checked out, committed or pushed |
| Migration file | `LMS_Backend/alembic/versions/2026_11_23_0632-0011_training_register_competency_.py` (untracked; revision `0011`, `down_revision = "0010"`) |
| Parent | `LMS_Backend/alembic/versions/2026_11_16_1500-0010_imports.py` (committed, unmodified) |

### 2.1 Migration review (before execution)

* `alembic heads` → a single head `0011`; `alembic history` → `0010 -> 0011 (head)`. No branches.
* Because the 0011 file is untracked, git cannot show whether it changed since review. Instead
  the SQL was regenerated offline (`alembic upgrade 0010:0011 --sql`, which makes no database connection) and compared
  with the reviewed preview `docs/database/migration-previews/0011_upgrade.sql`. The two are
  **byte-identical** (line endings normalised).
* Statement inventory of the SQL: 15 `CREATE TABLE`, 26 `CREATE INDEX`, 53 `FOREIGN KEY`,
  28 `CHECK`, 6 `INSERT INTO access_permission`, 2 `INSERT … SELECT INTO access_role_permission`,
  2 `INSERT INTO proficiency_scale`, 9 `INSERT INTO proficiency_level`, 1 `UPDATE alembic_version`.
  It contains no `ALTER`, `DROP`, `DELETE`, `TRUNCATE`, `RENAME` or `GRANT`. This matches package §1.
* Online-only Python paths (`_preflight`, the seed pre-check, `seed_problems`) issue only `SELECT`
  statements and raise on a mismatch. Destructive statements exist only in `downgrade()`, which
  was not run.
* `alembic/env.py`, `alembic.ini` and `app/db/` are unchanged from the commit. The only uncommitted
  change in `app/core/config.py` / `.env.example` adds `training_reminder_offsets_days`. It does not
  affect the database connection.

## 3. Target database identity

Read-only, as the migration account `lms_migrator@127.0.0.1` (credentials loaded from
`LMS_Backend/.env` through the project's `Settings`. The password was passed to `mysql.exe`
only through the child process environment and was never printed or written).

| Check | Result |
|---|---|
| Settings | `127.0.0.1 3306 crescent_lms_dev development`, runtime `lms_app`, migration `lms_migrator` |
| `CURRENT_USER()` / `@@port` / `VERSION()` / `DATABASE()` | `lms_migrator@127.0.0.1` / `3306` / `8.0.46` / `crescent_lms_dev` |
| Character set / collation | `utf8mb4` / `utf8mb4_0900_ai_ci` |
| `SHOW GRANTS` (before and after) | `USAGE ON *.*`; `SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, REFERENCES, INDEX, ALTER, TRIGGER ON crescent_lms_dev.*`. Unchanged |

## 4. Backup and restore assurance

| Item | Value |
|---|---|
| Dump | `C:\LMS_Backups\crescent_lms_dev_before_0011_20261123_194053.sql`, 116,733 bytes, read-only |
| SHA256 (recomputed before migration) | `7012086fced9570551ebf61584193b844e91ba4481e8e7c68f1106b3b64f3162`. **Matches** the approved value |
| Sidecar `.sql.sha256` | Same hash and file name; read-only |
| Baselines present | `.snapshot.json`, `.schema.txt` (43 lines), `.rows.txt` (39 lines), `.rows_after_dump.txt`, `.restore_schema.txt`, `.restore_rows.txt` |
| Dump consistency | `rows.txt` vs `rows_after_dump.txt`: identical |
| Restore test (into `crescent_lms_restore_0011`, performed earlier the same day) | `schema.txt` vs `restore_schema.txt`: **identical**. `rows.txt` vs `restore_rows.txt`: **identical**. Result: RESTORE VERIFICATION PASSED |

The backup files and the temporary restore database were not modified or deleted.

## 5. Pre-migration safety gates

| Gate | Result |
|---|---|
| A. Repository state | `master` @ `08758af`; migration, parent, Alembic environment and connection configuration reviewed (§2) |
| B. Backup validation | Passed (§4) |
| C. Live identity | Passed (§3) |
| D. Revision | `alembic current` → `0010` |
| E. Live DB = backup baseline | Fresh outputs `C:\LMS_Backups\crescent_lms_dev_preflight_0011_20261123_204502.{schema,rows}.txt` (43 / 39 lines). Both are **byte-identical** to the approved `.schema.txt` / `.rows.txt` |
| F. No LMS writer | No listener on 8010 or 4180; no LMS python/node/uvicorn process (`app.main:create_app`, `app.jobs`, `alembic`, `LMS_Backend`, `LMS_Frontend`); no enabled scheduled task referencing `app.jobs`/LMS. PMS (8000/5173) was not inspected or touched |
| G. Preflight summary | All gates passed; upgrade executed without a further confirmation, as authorised |

## 6. Execution

| Item | Value |
|---|---|
| Command | `.venv\Scripts\python -m alembic upgrade 0011` (cwd `LMS_Backend`), package §6.2 |
| Account | `lms_migrator@127.0.0.1` (via `LMS_MIGRATION_DB_*`) |
| Start / end | 2026-11-23 20:45:29 / 20:45:35 +05:30 |
| Exit code | **0** |
| Log | `C:\LMS_Backups\crescent_lms_dev_upgrade_0011_20261123_204528.log` |

Output (complete; stderr and stdout):

```text
INFO  [alembic.env] Connected to database crescent_lms_dev as lms_migrator@127.0.0.1
INFO  [alembic.runtime.migration] Context impl MySQLImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0010 -> 0011, First release: training register, competency library, skill matrices, notifications.
```

The command ran once. There was no retry, downgrade, `stamp`, manual SQL or seed script.

## 7. Post-migration verification

### 7.1 Revision

`alembic current` → `0011 (head)`. `alembic_version` holds exactly one row, `0011`.
`DATABASE()` is still `crescent_lms_dev`.

### 7.2 Snapshot comparison (package §6.3 b, runtime account)

Output of `db_readonly_snapshot.py --compare <…>.snapshot.json`. It is identical to the expected output in the package:

```text
database: crescent_lms_dev
revision: 0010 -> 0011
tables: 39 -> 54
foreign keys: 95 -> 148
triggers unchanged: True
0011 grants now: 12
tables added (15): competency, competency_assessment, competency_band_requirement, competency_level_descriptor, notification, notification_preference, proficiency_level, proficiency_scale, skill_matrix, skill_matrix_item, skill_matrix_member, training_event, training_participation, training_programme, training_session
tables removed (0): -
CHANGED access_permission: rows 30 -> 36, checksum same: False
CHANGED access_role_permission: rows 75 -> 87, checksum same: False
CHANGED alembic_version: rows 1 -> 1, checksum same: False
```

### 7.3 Structure (package §6.3 c, migration account)

Fresh outputs: `C:\LMS_Backups\crescent_lms_dev_after_0011_20261123_204545.{schema,rows}.txt`
(58 / 54 lines), compared with the approved baseline.

Schema differences. These are exactly the expected differences, and there are no others:

* `COUNTS` line changed from `tables=39 … columns=419 indexes=187 foreign_keys=95 checks=37 uniques=57 triggers=2 routines=0 events=0`
  to `tables=54 views=0 columns=620 indexes=286 foreign_keys=148 checks=65 uniques=81 triggers=2 routines=0 events=0`. This matches the package exactly.
* 15 added `TABLE` lines. Compared line-for-line with the 15 expected lines in package §6.3 (c)
  (engine, row format, collation, and hashes of columns, indexes, foreign keys and CHECK
  constraints): **all 15 identical**.
* `SCHEMA` line, both `TRIGGER` lines and all 39 pre-existing `TABLE` lines: **unchanged**.
  The structure of every original table, including columns, indexes, FKs, CHECKs and triggers, is intact.

Additional read-only checks on the new objects:

| Check | Result |
|---|---|
| New tables present | 15 / 15 (all names in §1 of the package) |
| Engine / table collation | 15 InnoDB, 15 `utf8mb4_0900_ai_ci`, row format Dynamic |
| Character columns in new tables | 66, all `utf8mb4_0900_ai_ci` |
| Foreign keys on new tables | 53, all `ON DELETE NO ACTION` / `ON UPDATE NO ACTION` |
| FKs from new tables into existing tables | `user_account` 21, `employee` 6, `org_unit` 3, `location` 2, `designation` 1, `functional_role` 1 |
| CHECK constraints on new tables | 28, all `ENFORCED = YES` |
| Distinct indexes on new tables | 99 (as measured on the test database) |
| Views / routines / events visible | 0 / 0 / 0 |

### 7.4 Permissions and role grants

| Permission | Description | Privileged |
|---|---|---|
| `competency.assess` | Record assessed proficiency levels for employees | 0 |
| `competency.manage` | Maintain proficiency scales, the competency library and skill matrices | 0 |
| `competency.view` | View every employee's skill matrices and competency assessments | 0 |
| `imports.organisation.commit` | Approve and commit a validated organisation-unit import | 0 |
| `imports.organisation.run` | Upload, map, validate and cancel organisation-unit imports | 0 |
| `training.records.view` | View every employee's training records and the full calendar | 0 |

* The new permissions are granted in exactly 12 rows: `hr_admin` × 6 and `super_admin` × 6. No other role holds them.
  All rows have `granted_by_user_id` NULL and `granted_at` set.
* Grants per role: `employee 3`, `hod 5`, `hr_admin 33` (was 27), `sme 5`, `super_admin 36`
  (was 30), `supervisor 5`. Total 87 = 87 distinct pairs (no duplicates).
* `access_permission`: 36 rows, 36 distinct codes (no duplicates).

### 7.5 Proficiency reference data

| Scale | Name | Method | Competent rank | Plan gap | Active | Version |
|---|---|---|---|---|---|---|
| `CF_SKILL_MATRIX_1_5` | Skill matrix scale (1-5) | ordinal | 3 | NULL | 1 | 1 |
| `CF_TC_LIBRARY_1_4` | Technical competency library scale (1-4) | numeric | NULL | 2 | 1 | 1 |

| Scale | Rank / code / label / numeric value |
|---|---|
| `CF_SKILL_MATRIX_1_5` | 1 L1 Beginner 1.00 · 2 L2 Can Work Under Supervision 2.00 · 3 L3 Can Work Independently 3.00 · 4 L4 Expert 4.00 · 5 L5 Can Train Others 5.00 |
| `CF_TC_LIBRARY_1_4` | 1 L1 Foundation 1.00 · 2 L2 Practitioner 2.00 · 3 L3 Advanced 3.00 · 4 L4 Expert 4.00 |

The source notes match the migration source. All 11 rows have a 16-byte `public_id`, and the IDs are distinct.
Timestamps are present. The scales have no default flag; the migration defines `is_active`
only.

### 7.6 Existing-data preservation

* Row comparison with the approved baseline: the only differing `ROWS` lines are
  `access_permission` (30 → 36), `access_role_permission` (75 → 87), `alembic_version`
  (1 → 1, new hash) and the 15 new tables (`proficiency_level 9`, `proficiency_scale 2`, 13 × `0 empty`).
  The other **36 pre-existing tables have identical row counts and content hashes**. These include employee,
  organisation, account, session, authentication, audit and import data.
* For the two changed permission tables, the pre-existing rows were re-hashed with the same
  method, excluding the rows the migration added:
  `access_permission` (30 rows) `470372ae…3f680ba8` and `access_role_permission` (75 rows)
  `6e7edf2f…7433241a`. Both are **identical to the baseline hashes**, so no existing permission
  or grant was altered.
* These are exactly the changes the migration source defines (6 + 12 inserts, the version
  update and the new tables). There are no unexplained differences.

### 7.7 Integrity

| Check | Result |
|---|---|
| Orphans across all 148 FK columns (single-column FKs only; no composite FKs exist) | **0** |
| Duplicate permission codes / role grants / seed public IDs | none |
| Audit triggers | `trg_audit_event_no_update` (BEFORE UPDATE) and `trg_audit_event_no_delete` (BEFORE DELETE) on `audit_event`, definer `lms_migrator@127.0.0.1`. Body and definer are unchanged per the fingerprint. They were not test-fired, because that would require a write attempt on `audit_event` |
| `alembic_version` | 1 row, `0011` |

### 7.8 Application compatibility (read-only smoke test)

As the runtime account `lms_app@127.0.0.1`, inside a `READ ONLY` transaction that was rolled back,
every ORM-mapped table (53 = 54 minus `alembic_version`) was queried with all of its mapped columns.
All succeeded, so the application models match the migrated schema. The application servers were
**not** started, and the package §7 interactive sign-in smoke test was not performed, because sign-in writes
session and audit rows.

## 8. Automated tests and static checks

Backend database tests run only against `crescent_lms_test` as `lms_test@127.0.0.1`. The harness
(`tests/support/database.py`) refuses any other name or account and re-checks `DATABASE()` /
`CURRENT_USER()` on every connection. Its schema rebuild of the test database is the documented
normal procedure (README, ADR-041). Frontend tests use mocked services and no database.

| Suite / check | Command | Result |
|---|---|---|
| Backend tests | `.venv\Scripts\python -m pytest` | **531 passed**, 0 failed, 4 warnings (53 min 52 s) |
| Ruff lint | `.venv\Scripts\python -m ruff check .` | All checks passed |
| Ruff format | `.venv\Scripts\python -m ruff format --check .` | 170 files already formatted |
| mypy (strict) | `.venv\Scripts\python -m mypy` | No issues in 169 source files |
| Frontend type check | `npm run typecheck` | Passed (exit 0) |
| Frontend lint | `npm run lint` | Passed (exit 0) |
| Frontend tests | `npm run test` | **395 passed** (35 files) |
| Frontend build | `npm run build` | Passed (exit 0) |
| Browser E2E | — | **Not run.** The repository contains no E2E configuration |

The four warnings all come from `test_migrations_and_models_do_not_drift`. They are Alembic
`UserWarning: Computed default on <column> cannot be modified` for the pre-existing stored
generated columns `employee_assignment.is_primary`, `employee_assignment.primary_open`,
`import_value_mapping.current_flag` and `user_account.linked_employee_active`. They are
informational, involve no 0011 table, and the drift test passed.

After the test run, both verification SQL files were run against `crescent_lms_dev` again
(`C:\LMS_Backups\crescent_lms_dev_after_0011_posttests_20261123_214136.{schema,rows}.txt`). The outputs are
**byte-identical** to the post-migration capture, which confirms the test suite did not touch the
development database. `alembic current` still reports `0011 (head)`.

## 9. Warnings, limitations and operational notes

* The 0011 migration file, approval package and verification SQL are **untracked** in git.
  Their integrity before execution was established by the offline SQL regeneration (§2.1),
  not by version control. Committing them is recommended.
* The approval package's `Status` line still reads "Not applied". It was intentionally not edited;
  this report is the record of execution.
* Rollback is a DBA operation (package §8). The 39-table backup alone does not remove the 15 new
  tables. `alembic downgrade` needs separate explicit approval.
* The routines/events count (0) is as seen by `lms_migrator`. The migration creates none.
* The seeded scales and the organisation import permissions reflect configuration choices that are still
  listed among the open business decisions (D-01…D-14). Changing them is out of scope here.

## 10. Final status and next action

`crescent_lms_dev` is at revision **`0011` (head)** with 54 tables, and its structure and data are verified
as intended. The LMS is still stopped. Recommended next step: start the backend on 8010 (with
`LMS_TRUSTED_ORIGINS` including 4180) and the frontend on 4180, then perform the package §7
smoke test as an HR Admin. Re-enable any task disabled for the migration (none was found
enabled), and commit the migration, approval package and this report once reviewed.

---

## 11. Post-Migration HR Admin Provisioning and Application Smoke Test — 24 November 2026

Sections 1–10 above are unchanged. This section records the package §7 smoke test, performed
with the database owner's written authorisation on 2026-11-24 (09:53–10:05 IST). The test made
no schema changes and ran no migration, downgrade, stamp, seed or test-database reset.

### 11.1 Method and credential handling

* **Services.** I started them with environment overrides only; no file or proxy configuration
  was edited.
  * Backend: `python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8010`,
    with `LMS_TRUSTED_ORIGINS` / `LMS_CORS_ALLOWED_ORIGINS` adding `http://localhost:4180` and
    `http://127.0.0.1:4180`.
  * Frontend: `npx vite --port 4180 --strictPort` with
    `LMS_DEV_API_PROXY_TARGET=http://127.0.0.1:8010`, as documented in the root README.
  * Note: `vite.config.ts` falls back to `http://127.0.0.1:8000` (the PMS port) when this
    variable is unset.
  * Nothing listened on 8000 or 5173, and PMS was not touched.
* **Client.** All calls went through the same-origin proxy `http://localhost:4180/api/v1`. They
  used a Python standard-library client (`urllib` + in-memory `CookieJar`), so no dependency was
  added; neither `httpx` nor Playwright is installed.
  * State-changing requests sent `Origin: http://localhost:4180`, plus the `X-CSRF-Token`
    returned by the session endpoints.
  * Cookies and CSRF tokens existed only in process memory and were never printed or written.
* **Passwords.**
  * The Super Admin password and the new account's permanent password were entered by the
    owner through `getpass` in a dedicated console window. The agent shell has no TTY.
  * The temporary password was generated with `secrets` in memory, never displayed, and
    discarded after the password change.
  * The permanent password was checked locally against the application's own
    `password_policy_issues` before submission, so no failed-change audit rows were produced.
* **Evidence location.** The helper scripts and the JSON evidence (statuses, counts, codes; no
  credentials, no employee data) are kept outside the repository in the agent session
  scratchpad. Database snapshots are in `C:\LMS_Backups`.

### 11.2 Pre-provisioning baseline

Snapshot: `C:\LMS_Backups\crescent_lms_dev_pre_smoke_20261124_095323.{schema,rows}.txt`, `.snapshot.json`, `.accounts.txt`

* **Identity.** `crescent_lms_dev`, `lms_app@127.0.0.1`, port 3306, MySQL 8.0.46, Alembic
  `0011`.
* **Accounts.** 2 accounts:
  * `Phoenix19`: active, `super_admin`.
  * `smoke.import.hradmin`: disabled, `hr_admin`.
  * `smoke.firstrelease.hradmin`: absent.
* **Comparison with the post-test capture of §8 (`…after_0011_posttests_20261123_214136`).**
  The schema is identical. The rows differ only in `audit_event` +1, `user_session` +1 and
  `user_account` (hash). These come from one owner sign-in as `Phoenix19` at
  2026-11-23 18:35:35 UTC (audit id 57, `auth.login.succeeded`), so this is not drift.

### 11.3 Account provisioning (supported API, Super Admin session)

Before starting, I confirmed that the Super Admin had `user_accounts.manage`,
`user_roles.assign_admin`, `user_accounts.view` and `audit.view`, and that the target login ID
did not exist.

| Op | Request | Result |
|---|---|---|
| A | `POST /admin/users` `{login_id, display_name, temporary_password, roles:["employee"]}` (email omitted) | 201, `pending_activation`, roles `[employee]`, public ID `01a20bcd-f5e8-7a76-8ec1-b46693ee8349` |
| B | `POST /admin/users/{id}/roles` `{"role":"hr_admin"}` | 200, roles `[employee, hr_admin]` |
| C | `POST /admin/users/{id}/activate` `{"reason":"First Release LMS smoke test onboarding"}` | 200, `active` |
| D | `GET /admin/users/{id}` | Login ID, display name, `active`, both roles, `password_must_change=true`, `email=null`, `employee=null`, status reason: all correct |

Audit (`GET /admin/audit-events?target_id=…`) recorded the following, all with outcome
`success` and actor `Phoenix19`:

* `user_account.created`
* `access_role.granted` (employee)
* `access_role.granted` (hr_admin)
* `user_account.activated` (`pending_activation → active`, with the reason)

### 11.4 First login and mandatory password change

| Step | Result |
|---|---|
| Sign-in with temporary password | 200, `password_must_change=true` |
| Protected read before change (`GET /employees`) | 403 `password_change_required`, so the requirement is enforced |
| `POST /auth/password` (the endpoint used by the frontend change-password page) | 200, `password_must_change=false`, session rotated |
| Sign-out, then fresh sign-in with the permanent password | 200, `active`, `must_change=false`, roles `[employee, hr_admin]` |
| Effective permissions | 33, equal to the 33 `hr_admin` grants (§7.4). The 3 `employee` permissions are a subset. `user_roles.assign_admin` and `access_roles.manage` are absent, which is correct |

### 11.5 Module smoke test (as `smoke.firstrelease.hradmin`, GET only)

**API** means authenticated API verification through the 4180 proxy.

**Browser** coverage is limited to this: the Vite server returned 200 for every listed SPA route,
and it transformed `src/main.tsx` and `src/app/router/routes.tsx` without error. **No browser
rendering or JavaScript console check was performed**, because no browser automation is
available.

| Module | Route | API calls (status) | API | Browser rendering |
|---|---|---|---|---|
| Dashboard | `/` | `/health/live`, `/health/ready`, `/training/calendar?mine=true`, `/training/summary`, `/notifications` all 200. `/competency/my-skills` returned 404 `employee_not_linked`, which is expected for an unlinked account; `SkillsWidget` hides itself | PASS | NOT TESTED |
| Organisation | `/organisation` | `/org/tree` (5 nodes), `/org/units` (5) 200 | PASS | NOT TESTED |
| Organisation chart | `/organisation/chart` | `/org/tree` 200 | PASS | NOT TESTED |
| Unit types | `/organisation/unit-types` | `/org/unit-types` 200 (3) | PASS | NOT TESTED |
| Other reference data | `/organisation/` locations, job-families, designations, grades, levels, functional-roles, responsibilities | All 200, all empty | PASS | NOT TESTED |
| Employees | `/employees` | `/employees` 200 (0 rows), `/employees/reporting-types` 200 | PASS | NOT TESTED |
| Training records | `/training` | `/training/events`, `/participations`, `/programmes`, `/calendar-labels` 200, all empty | PASS | NOT TESTED |
| Training calendar | `/training/calendar` | `/training/calendar` (42-day range) 200, empty | PASS | NOT TESTED |
| Competency library | `/competencies` | `/competency/competencies` 200 (0), `/categories` 200 | PASS | NOT TESTED |
| Proficiency scales | Competency library view | `/competency/scales` 200: both seeded scales, matching §7.5 exactly (method, competent rank / plan gap, all 9 levels with rank, code, label and value) | PASS | NOT TESTED |
| Skill Matrix | `/skills` | `/competency/matrices` 200 (0) | PASS | NOT TESTED |
| My Skills | `/skills/me` | 404 `employee_not_linked` (expected); `SkillsPages.tsx` renders a dedicated state for this code | PASS (expected 404) | NOT TESTED |
| Notifications | `/notifications` | `/notifications`, `/preferences`, `/channels` 200. `in_app` connected; `outlook` and `teams` show `connected=false` ("Not connected. Requires a Microsoft 365 app registration and IT approval.") | PASS | NOT TESTED |
| User accounts | `/admin/users` | 200: `Phoenix19` active, `smoke.firstrelease.hradmin` active, `smoke.import.hradmin` disabled | PASS | NOT TESTED |
| Imports | `/imports` (there is no `/admin/imports` route) | `/imports/profiles` 200 (2), `/imports` 200 (2 historical jobs), `/imports/mappings` 200 | PASS | NOT TESTED |
| Audit log | `/admin/audit-log` | `/admin/audit-events` 200 (50, more available) | PASS | NOT TESTED |
| RBAC read | — | `/admin/access-roles` 200 (6), `/admin/access-permissions` 200 (36); granted by `access_roles.view` | PASS | — |

No module issued a state-changing request. The only write caused by a read is the designed
`audit.events.viewed` audit record when the audit log is listed.

### 11.6 Backend request log

* The backend on 8010 logged 54 API requests in total. All of them arrived through the 4180
  proxy, which confirms the proxy target. Status breakdown: 47 × 200, 1 × 201, 3 × 204, 1 × 403,
  2 × 404.
* Every non-2xx response was expected:
  * The 403 is the deliberate `password_change_required` probe.
  * The two 404s are `employee_not_linked` on `/competency/my-skills`.
* There were no 401, 422 or 5xx responses, and no WARNING/ERROR entries or tracebacks. Backend
  stderr was empty.

### 11.7 Database before/after

Post-test snapshot: `C:\LMS_Backups\crescent_lms_dev_post_smoke_20261124_100354.{schema,rows}.txt`, `.snapshot.json`, `.accounts.txt`

* Schema fingerprint: **identical**. Alembic is `0011`, and 54 tables.
* Rows: **50 of 54 tables identical** (count and content hash). These include every employee,
  organisation, competency, training, notification, import, permission and role-grant table.
* The four changed tables are all authorised:

| Table | Before → after | Explanation |
|---|---|---|
| `user_account` | 2 → 3 | The new account. The password hash is held on this row; there is no separate credential table. `Phoenix19` `last_login_at`/`version` advanced (14 → 15) because of the sign-in; its status and roles are unchanged |
| `user_access_role` | 2 → 4 | `employee` and `hr_admin` grants for the new account |
| `user_session` | 19 → 23 | One Super Admin session and three HR Admin sessions (temporary password, rotation on password change, fresh sign-in). All four are now revoked by sign-out |
| `audit_event` | 53 → 66 | IDs 58–70: SA login, account created, 2 role grants, activation, `audit.events.viewed`, SA logout, HR login, password changed, HR logout, HR login, `audit.events.viewed`, HR logout |

* `login_throttle` is unchanged (2 rows), so there were no failed sign-ins. Account state after
  the test:
  * `Phoenix19`: active, `super_admin` only.
  * `smoke.import.hradmin`: disabled, unchanged (version 15, last login 2026-11-17).
  * `smoke.firstrelease.hradmin`: active, `must_change=0`, unlinked, roles `employee` and
    `hr_admin`.
* No other account was created, and no role or permission changed. The full orphan check of §7.7
  was not re-run. The only new rows are in the four identity/audit tables, written by the
  application through FK-constrained inserts.

### 11.8 Not tested / limitations

* **Browser UI rendering, layout, translations and JavaScript console:** NOT TESTED. Playwright
  or another browser automation tool is not installed, and none was added. A manual browser
  walkthrough as the new HR Admin is still needed.
* **Business data is almost empty.** There are 0 employees, training events, competencies and
  matrices, so the list views were verified only in their empty or near-empty state.
* **My Skills / dashboard skills widget** with a linked employee: not exercised, because the
  account is intentionally unlinked.
* **Not implemented as UI:** account creation. `/admin/users` is read-only, so provisioning used
  the API.
* **Outlook and Teams:** not connected, by design. No OAuth was attempted.

### 11.9 Result

**Smoke test partially passed.** Provisioning, activation, the mandatory password change, RBAC,
audit and every module API check passed, and database integrity is confirmed. Browser rendering
was not verified. The account `smoke.firstrelease.hradmin` remains **active** for the owner's
manual inspection. It is to be disabled later through `POST /admin/users/{id}/disable` with the
reason `First Release LMS smoke test completed`.

### 11.10 Browser Issue Investigation and Resolution — 24 November 2026

After §11.9, the owner walked through the whole application in a real browser as
`smoke.firstrelease.hradmin`. The console showed only two messages. Both were investigated from
the current code, the installed library sources and the live backend. Each was fixed in the
frontend; no backend code, API contract, schema or data was changed.

#### 11.10.1 Original console messages

| Issue | Message |
|---|---|
| A | ``client:364 No `HydrateFallback` element provided to render during initial hydration`` |
| B | `apiClient.ts:229 GET http://localhost:4180/api/v1/competency/my-skills 404 (Not Found)`, seen six times |

#### 11.10.2 Issue B — My Skills 404: root cause

Two causes were found: the 404 is deliberate (situation C), and the repeats come from the
frontend's refetch behaviour (situation E).

* **The endpoint exists and the URL is correct.** `GET /api/v1/competency/my-skills` is
  `my_skills` in `LMS_Backend/app/api/routes/competency.py`. A live, unauthenticated probe
  returned 401 `unauthenticated`, while an unknown path under the same prefix returned 404
  `not_found`. So the route is mounted, and the 4180 proxy reaches the 8010 backend.
* **The 404 is the documented contract.** `_employee_in_scope` raises
  `AppError(404, "employee_not_linked")` when the signed-in account has no `employee_id`. The
  account is intentionally unlinked, and §11.5–§11.6 had already recorded these 404s as
  expected. The page already shows its own message for this code.
* **Why the request repeated.** HTTP errors were never retried, because `retryTransient`
  returns false for HTTP errors. The repeats came from TanStack Query 5.107 refetch rules:
  * A query in the error state has no data, so it counts as stale.
  * By default, every new observer mount re-runs a query with no data (`retryOnMount`), and so
    does every window focus or network reconnect.
  * Two components observe this query: `MySkillsPage` and the dashboard `SkillsWidget`. Each
    visit to the dashboard or `/skills/me`, and each return to the browser tab, therefore sent
    the request again.
  * In development, StrictMode's mount → unmount → mount adds a request that is cancelled.
* **Reproduction.** A component test in StrictMode (open My Skills → dashboard → My Skills →
  window focus) recorded **7** requests before the fix.

#### 11.10.3 Issue A — HydrateFallback: root cause

* The application is a client-only SPA. It uses `createBrowserRouter(routes)` and
  `RouterProvider`, with no SSR and no `hydrationData`. Almost every page route uses `lazy`.
* React Router 8.5.1 (`lib/router/router.js`) works like this:
  * If any initially matched route still has an unresolved `lazy`, the router starts with
    `initialized = false` and `renderFallback = true`.
  * Until the lazy module loads, `lib/hooks.js` renders only the routes up to the nearest
    `HydrateFallback` or `hydrateFallbackElement`.
  * When there is none, it renders `null` for the root and logs this warning once.
* So "hydration" here means the router's *initial data load*, not server hydration. Nothing
  was enabled by accident. The real effect was a blank screen while the first route's code
  downloaded. Later navigations are not affected, because the current page stays visible.
* **Correct fix:** give the root route a `HydrateFallback`. Per-route fallbacks are not
  needed, because the fallback only applies to the first load. Hydration was not disabled, the
  router architecture was not changed, and no warning was suppressed.

#### 11.10.4 Corrections and files changed

| File | Change |
|---|---|
| `LMS_Frontend/src/lib/featureErrors.ts` | Added `isEmployeeNotLinked(error)`. It matches only HTTP **404 with code `employee_not_linked`**; every other 404 is unaffected |
| `LMS_Frontend/src/features/skills/competencyQueries.ts` | `useMySkills` now sets `retryOnMount`, `refetchOnWindowFocus` and `refetchOnReconnect` to "unless the last answer was `employee_not_linked`". Every other error, and every successful (linked) result, keeps the default behaviour. The answer stays in the cache for the session. The cache is purged at sign-out (`AuthProvider.purgePrivateData`), so the next sign-in asks again |
| `LMS_Frontend/src/features/auth/SessionScreens.tsx` | Moved the existing branded full-page loading layout (brand background, `BrandMark`, `LoadingState`) into an internal `BrandedLoadingScreen`. Added `AppLoadingScreen` ("Loading…", translated in all four languages via the existing `common.loading`). `SessionLoadingScreen` looks exactly as before |
| `LMS_Frontend/src/app/router/routes.tsx` | Added `HydrateFallback: AppLoadingScreen` to the root route. The `errorElement` and every route are unchanged |
| `LMS_Frontend/src/features/skills/skills.test.tsx` | Added regression tests (5 cases, below) |
| `LMS_Frontend/src/app/router/routes.test.tsx` | **New.** Router regression tests (4 cases, below) |
| `LMS_Backend/tests/integration/test_first_release_api.py` | Added `test_my_skills_distinguishes_unlinked_accounts` |

* **What was not changed:**
  * `MySkillsPage` (`SkillsPages.tsx`) and its locale strings. The empty-state wording and
    presentation are **preserved exactly**: "Your account is not linked to an employee
    record, so no personal skills can be shown."
  * The backend endpoint and its contract.
  * `apiClient.ts`.
  * The global query-client defaults.
* **Fallback design.** The fallback uses the same layout as the "checking session" screen that
  follows it on first load, so there is no layout shift. It is centred with `min-h-dvh` and a
  `px-4` gutter, which fits mobile, tablet and desktop. It has an accessible `role="status"`.
* **Remaining expected network entry.** An unlinked account still causes **one**
  `404 employee_not_linked` per signed-in session, on the first visit to the dashboard or My
  Skills. Browsers always list a non-2xx `fetch` in the console. This is the documented API
  answer, so it was left alone rather than hidden.
  * In the development server, StrictMode can add one entry marked *(canceled)*. This does not
    happen in a production build.
  * Removing the remaining entry would need an API change, for example exposing the employee
    link in the session payload. That is a decision for later, not part of this fix.

#### 11.10.5 Tests and checks (all run on 24 November 2026)

**Regression tests added.** Each was first run against the unfixed code: the 3 hydration
cases and the 2 unlinked-count cases **failed** (7 requests; warning logged). They pass with the
fix.

| Test | Scenario | Result |
|---|---|---|
| `skills.test.tsx` "shows the unchanged not-linked message and asks the server only once" (non-strict and StrictMode) | Unlinked account (synthetic 404 `employee_not_linked`) | Pass. The exact message and page description are shown; there is no table and no error card. Exactly **1** answered request across My Skills → dashboard → My Skills → window focus (exactly 1 fetch in total when not strict) |
| `skills.test.tsx` "still shows a linked employee their matrices and refreshes them normally" | Linked employee (synthetic grid fixture) | Pass. The matrix heading and grid render; the request is repeated normally on revisit |
| `skills.test.tsx` "reports another 404 / a server failure as an error and asks again" | 404 `employee_not_found`, 500 | Pass. "Your skills could not be loaded." is shown with retry, and the request is repeated on revisit. Genuine failures are not hidden |
| `routes.test.tsx` "shows the branded loading screen, then `/`, `/skills/me`, `/competencies`, without a hydration warning" (StrictMode) | Direct first load of each path | Pass. The first render is the "Loading…" status (not blank), then the page heading. No `HydrateFallback` warning |
| `routes.test.tsx` "navigates between sections after the first load" | `/` → organisation → employees → training → My Skills → competencies → `/` | Pass. Each heading renders and the pathname is correct |
| `test_first_release_api.py::test_my_skills_distinguishes_unlinked_accounts` | Synthetic unlinked `employee`+`hr_admin` account on `crescent_lms_test`; linked HR admin fixture | Pass. 404 `employee_not_linked` for the unlinked account; 200 with the account's own employee for the linked one. The existing linked-worker test (`test_seeded_scales_and_skill_matrix_gap_and_risk`) also passes |

**Full suites and static checks.**

| Check | Command | Result |
|---|---|---|
| Backend tests (full) | `.venv\Scripts\python -m pytest` (`crescent_lms_test` only) | **532 passed**, 0 failed, 4 warnings (24 min 47 s). The previous figure was 531; 1 test was added |
| Backend, first-release API file | `pytest tests/integration/test_first_release_api.py` | 8 passed |
| Ruff lint | `ruff check .` | All checks passed |
| Ruff format | `ruff format --check .` | 170 files already formatted |
| Mypy (strict) | `mypy` | Success: no issues found in 169 source files |
| Frontend typecheck | `npm run typecheck` | Pass (exit 0) |
| Frontend lint | `npm run lint` | Pass (exit 0) |
| Frontend tests | `npm run test` | **404 passed** (36 files). The previous figure was 395 in 35 files; 9 tests were added |
| Production build | `npm run build` | Pass (`tsc -b && vite build`, built in 11.6 s). `dist/` is gitignored |

#### 11.10.6 Browser verification status

* **Done:** component and router tests in jsdom (above). The running 4180 dev server compiled
  all four changed modules (HTTP 200, `HydrateFallback` present) and served `/`, `/skills/me`
  and `/competencies` (HTTP 200).
* **NOT done:** real browser rendering and console inspection. No browser automation is
  installed, and none was added. jsdom tests and a successful build do not prove a clean
  browser console. Owner recheck procedure (signed in as `smoke.firstrelease.hradmin`, DevTools
  Console and Network open with "Preserve log" on):
  1. Hard-reload `http://localhost:4180/`. Expect a short branded "Loading…" screen (not
     blank), then the dashboard. There should be no `HydrateFallback` warning.
  2. Open **My skills** (`/skills/me`). The heading, description and the unchanged not-linked
     message should show. Expect at most one `my-skills` 404 for the whole session. In dev, one
     extra *(canceled)* entry may appear.
  3. Open **Competency library** (`/competencies`) and the proficiency scales view. They should
     render normally.
  4. Return to the **Dashboard**, then switch to another window and back. There should be no
     new `my-skills` request.
  5. Optional: type `http://localhost:4180/skills/me` directly into the address bar. The
     branded loading screen should appear, then the page, with no warning.

#### 11.10.7 Database and account safety

* No migration, downgrade or stamp was run, and nothing was written to `crescent_lms_dev`.
  The database tests used only `crescent_lms_test`, whose identity is verified on every
  connection.
* `db_readonly_snapshot.py --compare …post_smoke_20261124_100354.snapshot.json` (runtime
  account, read-only transaction) reported:
  * Revision `0011 → 0011`, 54 tables, 148 foreign keys, triggers unchanged, 12 grants for the
    0011 permissions.
  * **51 of 54 tables identical**, including every employee, organisation, competency,
    training, notification, import, permission and role-grant table.
* The three changed tables came from the owner's manual browser session, which happened
  **before** this investigation:

| Table | Change | Cause |
|---|---|---|
| `audit_event` | 66 → 68 | id 71 `auth.login.succeeded` by `smoke.firstrelease.hradmin` (04:37 UTC); id 72 `audit.events.viewed` (04:40 UTC, audit log opened) |
| `user_session` | 23 → 24 | That sign-in |
| `user_account` | checksum | `smoke.firstrelease.hradmin` `last_login_at`/`version` 5 → 6 from that sign-in |

* **Account state** (read-only query):
  * `smoke.firstrelease.hradmin`: **active**, unlinked, roles `employee`, `hr_admin`
    (unchanged).
  * `Phoenix19`: active, `super_admin`, version 15. Unchanged since §11.7.
  * `smoke.import.hradmin`: **disabled**, `hr_admin`, version 15. Unchanged.

#### 11.10.8 Remaining limitations

* Real browser rendering and console are unverified until the owner completes the recheck in
  §11.10.6.
* The single expected `employee_not_linked` 404 per session remains by design (§11.10.4).
* The account still has no employee link, so the linked-employee path was verified only with
  synthetic test fixtures.

#### 11.10.9 Result

**Verification partially passed.** Both issues were traced to their causes and corrected with
frontend-only changes. Regression tests fail without the fixes and pass with them. All
automated checks pass, and the My Skills message is unchanged. The real-browser console recheck
by the owner is outstanding. `smoke.firstrelease.hradmin` remains **active**.

### 11.11 Final Verification and Closure — 24 November 2026

Sections 1–11.10 above are unchanged; §11.11.1 records the outcome of the recheck that
§11.10.6 left outstanding. This section was carried out with the database owner's written
authorisation of 2026-11-24 (11:00–11:10 IST). It made no schema change and ran no migration,
downgrade, stamp, seed or test-database reset. The only database writes were the authorised
account disable and the sign-in, audit and sign-out rows that the supported API records with it.

#### 11.11.1 Final manual browser verification (application owner)

**Type:** manual browser verification by the application owner in a real browser, after both
§11.10 fixes. This is **not** automated browser E2E: no browser automation is installed, and the
agent did not observe the browser. The results below are as confirmed by the owner.

| Check (§11.10.6 procedure) | Owner's result |
|---|---|
| Initial dashboard loading | Pass: the dashboard loads correctly |
| Hydration fallback | Pass: branded loading screen on first load, no `HydrateFallback` warning |
| My Skills empty state | Pass: the original, unchanged not-linked message is shown and is correct |
| My Skills request behaviour | Pass: behaves as designed in §11.10.4 (no repeated requests on revisit or window focus) |
| Competency library and proficiency scales | Pass: both render correctly |
| Navigation across the LMS modules | Pass: all pages work correctly |
| Browser console | No unexpected errors or warnings remain |

The single `404 employee_not_linked` network entry per session for an unlinked account remains
by design (§11.10.4) and is not an error.

The pre-disable capture (§11.11.4) showed exactly the three changed tables and row counts
already recorded in §11.10.7 (`audit_event` 68, `user_session` 24). No unexpected rows were
created.

#### 11.11.2 Final database integrity (read-only)

**Method:**
* The check ran as the runtime account `lms_app@127.0.0.1`, inside `START TRANSACTION READ ONLY`,
  issuing SELECT statements only, and was rolled back.
* FK definitions were read from `information_schema.REFERENTIAL_CONSTRAINTS` and
  `KEY_COLUMN_USAGE`, grouped per constraint in `ORDINAL_POSITION` order, so a composite FK is
  checked as one tuple.
* InnoDB uses MATCH SIMPLE semantics. A child row was counted as an orphan only when **all** of
  its FK columns are non-NULL and no parent row matches. Rows with a NULL FK column are valid by
  definition and were excluded.
* Triggers were listed with the migration account `lms_migrator@127.0.0.1`, also in a READ ONLY
  transaction that was rolled back. The runtime account lacks the TRIGGER privilege.

**Results** (run before the account disable, and again afterwards with identical results):

| Check | Result |
|---|---|
| Identity | `crescent_lms_dev`, MySQL 8.0.46 on `HIMESH-PC:3306` |
| Alembic | `alembic_version` holds one row: **`0011`** |
| FK constraints examined | **148**: `REFERENTIAL_CONSTRAINTS` has 148, and `KEY_COLUMN_USAGE` has 148 constraint groups. The two sets are identical |
| Composite FKs | 0 (all 148 are single-column) |
| FKs on nullable columns | 100 (NULL handled per MATCH SIMPLE, as above) |
| Rules | All `ON DELETE NO ACTION` / `ON UPDATE NO ACTION`. All FKs are within this schema |
| Failing constraints | **0** |
| Orphaned rows | **0** |
| Audit triggers | `trg_audit_event_no_delete` (BEFORE DELETE) and `trg_audit_event_no_update` (BEFORE UPDATE) on `audit_event`, definer `lms_migrator@127.0.0.1`. **Present and unchanged**, also per the schema fingerprint (§11.11.4) |

Note: `@@transaction_read_only` reports the session default, not the mode of an explicitly
started transaction, so it is not cited as evidence. Read-only behaviour is guaranteed by
`START TRANSACTION READ ONLY` together with SELECT-only statements.

#### 11.11.3 Smoke-test account closure

**Endpoint, verified in source before use:**
* `POST /api/v1/admin/users/{public_id}/disable` (`admin_users.disable_user` →
  `accounts.change_account_status`).
* Body `StatusChangeRequest {"reason": str ≤ 500 | null}`.
* Requires `user_accounts.manage`, a session cookie, and `X-CSRF-Token` (all unsafe methods).

**What the service does:**
* Checks that the transition `active → disabled` is allowed.
* Sets `status`, `status_reason`, `status_changed_at` and `deactivated_at`.
* Revokes every unrevoked session of the account with `revoked_reason = account_disabled`.
* Writes one `user_account.disabled` audit event with `from_status`, `to_status`, `reason` and
  `sessions_revoked`.
* It does not touch role grants or the employee link.

**Credential handling.** This was the same as §11.1:
* The Super Admin password was entered by the owner through `getpass` in a dedicated console
  window.
* Cookies and the CSRF token existed only in process memory, and requests went through the
  4180 proxy.
* No password, token or cookie was printed, logged or saved.

| Step | Result |
|---|---|
| `GET /health/ready` | 200 |
| Super Admin sign-in (`Phoenix19`) | 200. Holds `user_accounts.manage` and `audit.view`; no forced password change |
| Target identity (`GET /admin/users/01a20bcd-f5e8-7a76-8ec1-b46693ee8349`) | 200: `smoke.firstrelease.hradmin`, `active`, roles `employee`, `hr_admin`, employee `null` |
| Target active sessions (`GET …/sessions`) | 1: the owner's browser session from 04:37 UTC |
| **`POST …/disable` `{"reason":"First Release LMS smoke test completed"}`** | **200, `disabled`** |
| Re-read (`GET`) | Status `disabled`, reason exact, roles `employee` and `hr_admin` retained, employee `null` |
| Target active sessions | **0** |
| Audit (`GET /admin/audit-events?target_id=…`) | Exactly one `user_account.disabled`, outcome `success`, actor `Phoenix19`, metadata `{from_status: active, to_status: disabled, reason: "First Release LMS smoke test completed", sessions_revoked: 1}` (audit id 74, 2026-11-24 05:34:26 UTC) |
| Account list before and after | Only `smoke.firstrelease.hradmin` changed (`active → disabled`) |
| Super Admin sign-out | 204 |

**Final account state** (read-only database query after the disable):

| Account | State |
|---|---|
| `smoke.firstrelease.hradmin` | **`disabled`**. Reason `First Release LMS smoke test completed`. `status_changed_at` = `deactivated_at` = 2026-11-24 05:34:26.588520 UTC. Roles `employee` and `hr_admin` still granted (unrevoked). `employee_id` NULL. `password_must_change` unchanged (false). Version 6 → 7. Sessions: 4 in total, 0 unrevoked; the live one was revoked with `account_disabled` |
| `Phoenix19` | `active`, `super_admin` only. `last_login_at` and version 15 → 16 changed **only** because of this task's sign-in |
| `smoke.import.hradmin` | `disabled`, `hr_admin`, version 15. **Unchanged** |

The owner's browser tab, which was signed in as the smoke account, is now signed out, and the
account can no longer sign in. It was **not** deleted. Its password was not reset, and its roles
and employee linkage were not modified.

#### 11.11.4 Final database comparison

New read-only captures were taken with the same tooling as §11.2 and §11.7, using the migration
account for the fingerprint/hash SQL and the runtime account for the snapshot. No earlier file
was overwritten.

* `C:\LMS_Backups\crescent_lms_dev_pre_disable_20261124_110311.{schema,rows}.txt`, `.snapshot.json`, `.accounts.txt`
* `C:\LMS_Backups\crescent_lms_dev_post_disable_20261124_110450.{schema,rows}.txt`, `.snapshot.json`, `.accounts.txt`

**Compared with the post-disable capture,** both the §11.7 post-smoke capture
(`…post_smoke_20261124_100354`) and the pre-disable capture show:

* Schema fingerprint: **identical** (0 differing lines).
* Alembic `0011`, 54 tables, 148 FKs, triggers unchanged, 12 grants for the 0011 permissions.
* Rows: **51 of 54 tables identical** by count and content hash.

Differences caused by the disable (pre-disable → post-disable):

| Table | Change | Explanation |
|---|---|---|
| `audit_event` | 68 → 72 | Id 73 `auth.login.succeeded` (`Phoenix19`), id 74 `user_account.disabled`, id 75 `audit.events.viewed` (the audit verification read), id 76 `auth.logout` |
| `user_session` | 24 → 25 | +1 Super Admin session, revoked by its sign-out. The target's one live session was revoked (`account_disabled`) |
| `user_account` | 3 → 3 (hash) | Target: status, reason, `status_changed_at`, `deactivated_at`, `updated_by_user_id`, version. `Phoenix19`: `last_login_at` and version, from the sign-in |

Against the post-smoke capture there are also `audit_event` 66 → 68, `user_session` 23 → 24 and
the target's `last_login_at`. These come from the owner's 04:37 UTC browser sign-in, already
explained in §11.10.7.

**Unchanged:**
* `user_access_role`: 4 rows, identical, so no role assignment was removed.
* `login_throttle`: 2 rows, so there were no failed sign-ins.
* Every employee, organisation, occupational-reference, training, competency, skill-matrix,
  notification, import, permission and role-grant table.

No separate account-status history table exists: status history is carried by `user_account`
and `audit_event`. The database is **not** claimed to be byte-identical to an earlier snapshot,
because the disable and its audit trail are authorised writes. Every difference is listed above.

#### 11.11.5 Evidence retained

* The accepted pre-0011 backup `C:\LMS_Backups\crescent_lms_dev_before_0011_20261123_194053.sql`
  and its `.sha256` (`7012086f…3f162`) are unchanged and still read-only.
* Every earlier snapshot, baseline and comparison file in `C:\LMS_Backups` is preserved.
* The restore database `crescent_lms_restore_0011` was neither accessed nor modified.
* This task's helper scripts and JSON results (integrity results before and after, account and
  session state before and after, disable-step evidence) contain no credentials. They are in the
  agent session scratchpad, which is temporary; the durable evidence is the `C:\LMS_Backups`
  captures and this report.

#### 11.11.6 Final verification conclusion

**The first-release technical verification cycle is complete.**

* Migration `0011` is applied and verified (§7).
* Referential integrity is confirmed: 148 FKs, 0 orphans, both audit triggers present.
* The automated suites passed (§11.10.5: backend 532, frontend 404, lint, types and build).
  They were not re-run in this closure task, which changed no application code.
* The owner's manual browser verification passed.
* The synthetic HR Admin account is disabled, with its audit trail recorded.

Outstanding limitations (none blocks the commit):
* There is no automated browser E2E suite in the repository. Browser coverage is the owner's
  manual check.
* Business data is almost empty: 0 employees, events, competencies and matrices. The list
  views were verified in their empty or near-empty states, and the linked-employee My Skills
  path only with synthetic test fixtures.
* One `employee_not_linked` 404 per session for unlinked accounts remains by design.
* Outlook and Teams are not connected, by design.
* Scheduling `app.jobs training-reminders` was not part of this verification.
* Open business decisions D-01…D-14 remain
  (`docs/reference-analysis/05_SOURCE_TO_SYSTEM_MAPPING_AND_OPEN_DECISIONS.md`).
* A rollback of `0011` needs a DBA (§9).
* The first-release work is still **uncommitted**. Committing it is the owner's decision.
