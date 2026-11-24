# Migration 0011 — Approval Package

| | |
|---|---|
| **Date** | 2026-11-23 (post-implementation review; backup / restore / verification procedure re-validated the same day) |
| **Target** | `crescent_lms_dev` on `127.0.0.1:3306`, MySQL 8.0.46 |
| **Current revision** | `0010` (verified read-only with `alembic current`, `SELECT version_num` and `scripts/db_readonly_snapshot.py`) |
| **Revision file** | `LMS_Backend/alembic/versions/2026_11_23_0632-0011_training_register_competency_.py` |
| **SQL preview** | [`migration-previews/0011_upgrade.sql`](migration-previews/0011_upgrade.sql), [`0011_downgrade.sql`](migration-previews/0011_downgrade.sql) — regenerated 2026-11-23 with `alembic … --sql` (the earlier preview was stale: it omitted the two `imports.organisation.*` permissions and their four grants) |
| **Verification SQL** | [`verification/schema_fingerprint.sql`](verification/schema_fingerprint.sql), [`verification/table_content_hashes.sql`](verification/table_content_hashes.sql) — read-only, run through `mysql.exe` (§5) |
| **Status** | **Not applied.** Applying it requires the owner's explicit approval. |

## 1. What the migration does (verified from the regenerated preview)

| Class | Count | Details |
|---|---:|---|
| New tables | 15 | `notification_preference`, `proficiency_scale`, `proficiency_level`, `competency`, `competency_band_requirement`, `competency_level_descriptor`, `skill_matrix`, `training_programme`, `competency_assessment`, `skill_matrix_item`, `skill_matrix_member`, `training_event`, `notification`, `training_participation`, `training_session` |
| Alterations of existing tables | **0** | No `ALTER TABLE`, `DROP`, `TRUNCATE` or `UPDATE` of existing data (only Alembic's own `alembic_version` row) |
| Secondary indexes | 26 | `CREATE INDEX`, all on new tables (plus 15 primary keys and 24 inline UNIQUE constraints; MySQL adds further indexes to back foreign keys — 99 distinct indexes on the new tables in total, measured on the test database) |
| Foreign keys | 53 | All on new tables, referencing new tables or `user_account`, `employee`, `org_unit`, `location`, `designation`, `functional_role`. No `ON DELETE` actions (MySQL default `RESTRICT`/`NO ACTION`): nothing cascades into or out of existing data |
| CHECK constraints | 28 | Evidence rules (e.g. completed event needs actual start date; completion needs present/partial attendance; certificate needs completion; competency `status` in draft/approved; approved needs `approved_at`) |
| Rows inserted into **existing** tables | 18 | `access_permission`: `training.records.view`, `competency.view`, `competency.manage`, `competency.assess`, `imports.organisation.run`, `imports.organisation.commit` (all `is_privileged = false`). `access_role_permission`: those 6 × roles `hr_admin` and `super_admin` = 12 grants (two `INSERT … SELECT`). No other role receives anything |
| Reference rows in new tables | 11 | `proficiency_scale` `CF_SKILL_MATRIX_1_5` (ordinal, skilled from rank 3) and `CF_TC_LIBRARY_1_4` (numeric, plan at gap ≥ 2); 5 + 4 `proficiency_level` rows |
| Triggers, views, routines, events, MySQL account privileges | 0 | The migration creates none and changes no `GRANT` |
| Other data manipulation | 0 | |

Expected after upgrade (exact values in §6): 54 tables (39 + 15), 148 foreign keys (95 + 53),
65 CHECK constraints (37 + 28), 36 permissions, 87 role grants (75 + 12). Every pre-existing
table except `access_permission`, `access_role_permission` and `alembic_version` keeps the
same row count **and the same per-row content hash** (§5.3), and all 39 pre-existing tables keep
the same structure (columns, indexes, foreign keys, CHECK constraints, triggers).

## 2. Safety properties

| Property | Behaviour | Evidence |
|---|---|---|
| Pre-flight | Refuses to start, changing nothing, if any of the 15 tables already exists (left by an interrupted attempt — MySQL DDL is not transactional) and explains recovery | `test_upgrade_preflight_refuses_leftover_tables_without_changing_anything` |
| Seed idempotency | Refuses if any of the 6 permission codes already exists or a target role is missing; after seeding, verifies exact permissions and exactly 12 mappings, else fails | `seed_problems`, `test_clean_round_trip_and_exact_seed` |
| Partial failure | DDL commits per statement; a failure leaves `alembic_version` at `0010`. Recovery: §8 (restore) or, after confirming the new tables are empty, have a DBA drop them; the pre-flight then allows a clean retry | Pre-flight test above |
| Downgrade guard | Refuses, changing nothing, while any training / competency / matrix / assessment / notification / preference row exists, a non-seeded scale exists, **the seeded scales or their levels were edited**, **organisation import jobs exist**, or the permission seed/grants were changed | `test_downgrade_refuses_*` (4 tests) |
| Downgrade data | Deletes only the 6 permissions, their 12 grants and the two seeded scales, then drops the 15 empty tables | `0011_downgrade.sql` |
| MySQL compatibility | CHECK constraints are enforced from MySQL 8.0.16; server is 8.0.46. Upgrade → downgrade → upgrade verified on `crescent_lms_test` | Migration-safety suite; ORM/migration drift test |

Downgrades on `crescent_lms_dev` additionally require explicit approval and a verified
backup. No downgrade experiment was run on the development database.

## 3. Database facts that determine the backup method (verified read-only, 2026-11-23)

Collected with `SHOW GRANTS` and `information_schema` queries inside
`START TRANSACTION READ ONLY` as `lms_migrator` and `lms_app`, and with the two verification
SQL files run through `mysql.exe`. Nothing was written, dumped, restored, created or dropped.

### 3.1 Accounts

| Account | Exact grants |
|---|---|
| `lms_migrator`@`127.0.0.1` | `GRANT USAGE ON *.*` · `GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, REFERENCES, INDEX, ALTER, TRIGGER ON crescent_lms_dev.*`. No roles. No table- or column-level grants. |
| `lms_app`@`127.0.0.1` | `GRANT USAGE ON *.*` · `GRANT SELECT, INSERT, UPDATE, DELETE ON crescent_lms_dev.*`. No roles. |

What `mysqldump` needs, and whether `lms_migrator` has it:

| Requirement | Needed for | `lms_migrator` | Consequence |
|---|---|---|---|
| `SELECT` on every table | table data | **Yes** (schema-wide, all 39 tables) | — |
| `TRIGGER` | `--triggers` (default on) | **Yes** | The 2 triggers are dumped |
| `SHOW VIEW` | views | **No** | Irrelevant: there are **0 views** (authoritative — `information_schema.TABLES` lists every view the account could select from) |
| Global `SELECT` or `SHOW_ROUTINE` | `--routines` | **No** | `lms_migrator` cannot see routines defined by other accounts, so `--routines` would silently dump nothing. It sees 0; no migration creates any. A DBA must confirm 0 (§4.3) |
| `EVENT` | `--events` | **No** | Same: it sees 0 events but cannot see events it lacks `EVENT` on. A DBA must confirm 0 (§4.3) |
| `PROCESS` | tablespace listing | **No** | Avoided by `--no-tablespaces` |
| `LOCK TABLES` | `--lock-tables` | **No** | Not used: `--single-transaction` turns table locking off |
| `RELOAD` / `FLUSH_TABLES` | `FLUSH TABLES WITH READ LOCK` | **No** | Not issued: `gtid_mode = OFF` and `--set-gtid-purged=OFF`, and no `--source-data` |
| `LOCK TABLES` on the **target** | restoring (the dump contains `LOCK TABLES … WRITE` from `--add-locks`) | **No** | `lms_migrator` cannot restore the dump into `crescent_lms_dev`; restores (test and rollback) are DBA operations |

**Decision.** `lms_migrator` may take the backup **only after** a DBA has confirmed, with an
account that can see them, that `crescent_lms_dev` has 0 routines and 0 events (§4.3 gate).
The command then omits routines and events explicitly (`--skip-routines --skip-events`):
with nothing to dump, the flags add nothing, and keeping `--routines` would only suggest a
coverage the account cannot provide. If the DBA finds any routine or event, **the DBA takes
the backup** with `--routines --events` (§4.4, variant B). Whether `lms_migrator`'s
`mysqldump` succeeds is itself unverified until it runs; the exit-code gate catches failure,
in which case the DBA takes the backup.

### 3.2 Schema, engines and objects

| Item | Value |
|---|---|
| Server | MySQL 8.0.46 Community (client `mysqldump`/`mysql` 8.0.46 in `C:\Program Files\MySQL\MySQL Server 8.0\bin`, not on `PATH`) |
| `crescent_lms_dev` default character set / collation | `utf8mb4` / `utf8mb4_0900_ai_ci` (read from `information_schema.SCHEMATA`; server defaults are the same) |
| Tables | 39 base tables, **all InnoDB**, row format `Dynamic`, collation `utf8mb4_0900_ai_ci`; no partitions; all 114 character columns `utf8mb4_0900_ai_ci` |
| Views / routines / events | 0 / 0 (as seen by `lms_migrator`, DBA to confirm) / 0 (as seen by `lms_migrator`, DBA to confirm). `event_scheduler` is `ON` server-wide but no event exists in this schema |
| Triggers | 2: `trg_audit_event_no_update` (BEFORE UPDATE) and `trg_audit_event_no_delete` (BEFORE DELETE) on `audit_event`, `DEFINER = lms_migrator@127.0.0.1`, `SIGNAL` only |
| Structure | 419 columns, 187 distinct indexes, 95 foreign keys (all `NO ACTION`), 37 CHECK constraints, 57 UNIQUE constraints, 15 stored generated columns |
| Special column types | 31 `binary(16)` (`public_id` etc.) and 8 `json` columns |
| Binary log | `log_bin = ON`, `binlog_format = ROW`, `log_bin_trust_function_creators = 1`, `gtid_mode = OFF`, `lower_case_table_names = 1` |
| Data today | 16 of 39 tables hold rows (about 210 rows in all). Row counts change whenever the LMS is used (sign-ins write `user_session`, `login_throttle`, `audit_event`), so the snapshot taken at backup time, not this table, is the reference |
| Free space | C: about 191 GB free; the schema occupies about 3.5 MB of pages. Expected dump size is roughly 100 KB (the same command against the 54-table test database produced 118 KB) |

Consequences:

* `--single-transaction` is correct: every table is InnoDB, so the dump is one consistent
  snapshot without locking. The procedure additionally stops every LMS writer and proves
  that no row changed while the dump ran (§4.5).
* `--hex-blob` is added so the 31 `binary(16)` columns are written as `0x…` literals instead
  of raw bytes inside a UTF-8 text file. Stored generated columns are recomputed on restore;
  the content hashes in §5 cover them.
* The restore database must be created `CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci`
  (verified above, not assumed). Table and column collations are explicit in the dump.
* Because the trigger `DEFINER` (`lms_migrator@127.0.0.1`) differs from the DBA account, the
  restoring account needs `SET_USER_ID` (or the deprecated `SUPER`).
  `log_bin_trust_function_creators = 1`, so binary logging adds no further requirement.

## 4. Backup procedure

Legend: **[SAFE]** read-only or local-file only · **[WRITES FILE]** creates files in the backup
folder only · **[DBA]** needs an administrator account · **[MODIFIES DEV — APPROVAL
REQUIRED]** changes `crescent_lms_dev`.

**How to run.** Use a Windows PowerShell 5.1 *console* window (not the ISE: the `-p` password
prompts need a console). Paste one block at a time. Every check block is wrapped in
`. { … }` on purpose. A `throw` inside it stops the **whole block**; pasting bare lines would
let the next line run after a failure. If a block stops with an error, **do not continue**:
resolve it, then restart from the step the error names.

**Credentials** never appear on a command line or in this document: `-p` makes `mysql.exe` /
`mysqldump.exe` prompt, and the snapshot script reads `LMS_DB_*` from `LMS_Backend\.env`.
Expect one password prompt per `mysql.exe` / `mysqldump.exe` call.

**Encoding.** The SQL dump is written by `mysqldump.exe` itself (`--result-file`). Never use
`>` or `| Out-File` for a dump: Windows PowerShell 5.1 re-encodes native output, and `>`
writes UTF-16. Only the small text outputs (snapshot JSON and verification lines, all ASCII)
pass through PowerShell. The snapshot JSON is written with `Out-File -Encoding utf8`, which
in 5.1 means UTF-8 **with** a byte-order mark. `db_readonly_snapshot.py --compare` opens it
with `utf-8-sig`, which accepts the BOM, and the JSON is pure ASCII (`json.dumps` default
`ensure_ascii`). Verified by round-trip on 2026-11-23. Do **not** create it with `>`: the
resulting UTF-16 file cannot be read by `--compare`.

### 4.0 Variables and helper [SAFE]

Run in every new PowerShell session used for this procedure. The DBA's session (§5) sets
`$Stamp` to the value recorded at backup time instead of a new one.

```powershell
$ErrorActionPreference = 'Stop'
$Repo      = 'D:\OneDrive - CRESCENT FOUNDRY CO. PVT. LTD\Desktop\CF Projects\LMS'
$Backend   = Join-Path $Repo 'LMS_Backend'
$VerifyDir = Join-Path $Repo 'docs\database\verification'
$MySqlBin  = 'C:\Program Files\MySQL\MySQL Server 8.0\bin'      # not on PATH
$MySqlDump = Join-Path $MySqlBin 'mysqldump.exe'
$MySql     = Join-Path $MySqlBin 'mysql.exe'
$DbHost    = '127.0.0.1'; $DbPort = '3306'; $DbName = 'crescent_lms_dev'
$BackupDir = 'C:\LMS_Backups'      # outside the repository and outside OneDrive sync
$Stamp     = Get-Date -Format 'yyyyMMdd_HHmmss'    # DBA session: $Stamp = '<recorded stamp>'
$Base          = Join-Path $BackupDir "crescent_lms_dev_before_0011_$Stamp"
$Dump          = "$Base.sql"
$DumpPartial   = "$Base.sql.partial"
$DumpSha       = "$Base.sql.sha256"
$Before        = "$Base.snapshot.json"
$BeforeSchema  = "$Base.schema.txt"
$BeforeRows    = "$Base.rows.txt"
$AfterDumpRows = "$Base.rows_after_dump.txt"
Set-Location $Backend
"Backup stamp: $Stamp   (write this down)"

function Invoke-LmsSqlFile([string]$User, [string]$Database, [string]$SqlFile, [string]$OutFile) {
  # Runs one read-only verification SQL file with mysql.exe; refuses to overwrite output.
  if (Test-Path -LiteralPath $OutFile) { throw "Refusing to overwrite existing $OutFile" }
  if (-not (Test-Path -LiteralPath $SqlFile)) { throw "Missing $SqlFile" }
  $src = $SqlFile -replace '\\', '/'
  $lines = @(& $MySql -h $DbHost -P $DbPort -u $User -p --default-character-set=utf8mb4 `
              --batch --skip-column-names --raw "--database=$Database" -e "source $src")
  if ($LASTEXITCODE -ne 0) { throw "mysql.exe exited with $LASTEXITCODE running $SqlFile on $Database" }
  if ($lines.Count -eq 0) { throw "No output from $SqlFile on $Database" }
  $lines | Set-Content -LiteralPath $OutFile -Encoding Ascii
  "{0}: {1} lines" -f (Split-Path -Leaf $OutFile), $lines.Count
}
```

### 4.1 Executables, folder and disk space [SAFE] / [WRITES FILE: creates the folder]

```powershell
. {
  foreach ($exe in $MySqlDump, $MySql) { if (-not (Test-Path -LiteralPath $exe)) { throw "Not found: $exe" } }
  & $MySqlDump --version; if ($LASTEXITCODE -ne 0) { throw 'mysqldump --version failed' }
  & $MySql --version;     if ($LASTEXITCODE -ne 0) { throw 'mysql --version failed' }
  if (-not (Test-Path -LiteralPath $BackupDir)) { New-Item -ItemType Directory -Path $BackupDir | Out-Null }
  if ($BackupDir -like "$Repo*" -or $BackupDir -like '*OneDrive*') { throw 'Backup folder must be outside the repository and OneDrive' }
  $drive = Get-PSDrive -Name (Split-Path -Qualifier $BackupDir).TrimEnd(':')
  '{0:N1} GB free on {1}:' -f ($drive.Free / 1GB), $drive.Name
  if ($drive.Free -lt 1GB) { throw 'Less than 1 GB free on the backup drive' }
  foreach ($f in $Dump, $DumpPartial, $DumpSha, $Before, $BeforeSchema, $BeforeRows, $AfterDumpRows) {
    if (Test-Path -LiteralPath $f) { throw "Already exists, refusing to overwrite: $f" } }
  'OK: executables, folder, space'
}
```

Expected: both versions `Ver 8.0.46 for Win64 on x86_64`, at least 1 GB free (about 191 GB
today), `OK`.

The dump contains password hashes, session records and audit data. Keep `C:\LMS_Backups`
readable only by administrators and the person responsible for the backup. Never copy it
into the repository or a synced OneDrive folder.

### 4.2 Stop every LMS process that writes [SAFE — stops only LMS processes, by hand]

LMS database writers: the backend (uvicorn on port 8010), the CLI `python -m app.jobs …`
(e.g. the training-reminder job, if it was scheduled) and Alembic. The frontend on 4180 does
not write to the database and may keep running. Tests use `crescent_lms_test`, not the dev
database. **Never stop PMS (ports 8000 / 5173) or any unidentified process.**

Stop the backend with Ctrl+C in its own terminal (uvicorn `--reload`). If a Windows
scheduled task runs `app.jobs`, disable it in Task Scheduler for the duration. Then confirm:

```powershell
. {
  $listen = @(Get-NetTCPConnection -State Listen -LocalPort 8010 -ErrorAction SilentlyContinue)
  $procs  = @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
              Where-Object { $_.CommandLine -match 'app\.main:create_app|app\.jobs|alembic' -or
                             $_.ExecutablePath -like "$Backend\*" } |
              Select-Object ProcessId, CommandLine)
  $tasks  = @(Get-ScheduledTask | Where-Object { $_.State -ne 'Disabled' -and
              (($_.Actions | ForEach-Object { "$($_.Execute) $($_.Arguments)" }) -join ' ') -match 'app\.jobs' } |
              Select-Object TaskPath, TaskName, State)
  $listen; $procs | Format-List; $tasks
  if ($listen.Count -or $procs.Count -or $tasks.Count) { throw 'An LMS writer is still active (see above). Stop it, then re-run this block.' }
  'OK: no LMS listener on 8010, no LMS python process, no enabled app.jobs task'
}
```

Keep the LMS stopped until §6 has been completed (or, if the owner does not approve the
upgrade, until the backup is verified).

### 4.3 Confirm connection identity, revision and objects [SAFE] (+ one DBA query)

```powershell
.venv\Scripts\python -c "from app.core.config import Settings; s=Settings(); print(s.db_host, s.db_port, s.db_name, s.environment.value, 'runtime:', s.db_user, 'migration:', s.migration_db_user)"
# Expect exactly: 127.0.0.1 3306 crescent_lms_dev development runtime: lms_app migration: lms_migrator

. {
  $rev = @(.venv\Scripts\python -m alembic current)
  if ($LASTEXITCODE -ne 0) { throw "alembic current failed ($LASTEXITCODE)" }
  $rev
  if (($rev -join ' ').Trim() -notmatch '^0010\b') { throw 'Revision is not 0010: stop' }
  $id = @(& $MySql -h $DbHost -P $DbPort -u lms_migrator -p --batch --skip-column-names "--database=$DbName" `
          -e "SELECT CURRENT_USER(), @@port, VERSION(), DATABASE(), (SELECT version_num FROM alembic_version)")
  if ($LASTEXITCODE -ne 0) { throw "mysql.exe failed ($LASTEXITCODE)" }
  $id
  if ($id.Count -ne 1 -or $id[0] -ne "lms_migrator@127.0.0.1`t3306`t8.0.46`tcrescent_lms_dev`t0010") { throw 'Unexpected identity or revision: stop' }
  'OK: lms_migrator@127.0.0.1 on 3306, MySQL 8.0.46, crescent_lms_dev, revision 0010'
}
```

**DBA gate (read-only).** Before `lms_migrator` takes the backup, a DBA runs this with an
account that can see every routine and event, and records the result:

```powershell
& $MySql -h $DbHost -P $DbPort -u <dba-account> -p --table -e "SELECT (SELECT COUNT(*) FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA='crescent_lms_dev') AS routines, (SELECT COUNT(*) FROM information_schema.EVENTS WHERE EVENT_SCHEMA='crescent_lms_dev') AS events, (SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='crescent_lms_dev' AND TABLE_TYPE='VIEW') AS views"
```

Expected: `routines 0 | events 0 | views 0`. Any non-zero value: the DBA takes the backup
(§4.4 variant B).

### 4.4 Snapshot, then dump [WRITES FILE] (read-only on the database)

```powershell
. {
  # (a) reference snapshot: runtime account, READ ONLY transaction (row counts, CHECKSUM TABLE, 0011 grants)
  .venv\Scripts\python ..\scripts\db_readonly_snapshot.py | Out-File -LiteralPath $Before -Encoding utf8 -NoClobber
  if ($LASTEXITCODE -ne 0) { throw "Snapshot failed ($LASTEXITCODE). Delete the incomplete $Before, then re-run this block." }
  $snap = Get-Content -LiteralPath $Before -Raw -Encoding UTF8 | ConvertFrom-Json
  if ($snap.database -ne 'crescent_lms_dev' -or $snap.alembic_revision -ne '0010' -or $snap.table_count -ne 39 -or $snap.foreign_key_count -ne 95) {
    throw "Unexpected snapshot: $($snap.database) $($snap.alembic_revision) $($snap.table_count) $($snap.foreign_key_count)" }
  # (b) structure and content baseline: migration account (sees triggers)
  Invoke-LmsSqlFile lms_migrator $DbName (Join-Path $VerifyDir 'schema_fingerprint.sql')   $BeforeSchema
  Invoke-LmsSqlFile lms_migrator $DbName (Join-Path $VerifyDir 'table_content_hashes.sql') $BeforeRows
  'OK: baseline captured'
}
```

Expected: `….schema.txt: 43 lines` (1 SCHEMA, 1 COUNTS, 39 TABLE, 2 TRIGGER) and
`….rows.txt: 39 lines`. The COUNTS line must read exactly:

```text
COUNTS tables=39 views=0 columns=419 indexes=187 foreign_keys=95 checks=37 uniques=57 triggers=2 routines=0 events=0
```

**Variant A — `lms_migrator` (DBA gate passed):**

```powershell
. {
  if (Test-Path -LiteralPath $DumpPartial) { throw "Refusing to overwrite $DumpPartial" }
  if (Test-Path -LiteralPath $Dump)        { throw "Refusing to overwrite $Dump" }
  & $MySqlDump -h $DbHost -P $DbPort -u lms_migrator -p `
    --single-transaction --triggers --skip-routines --skip-events --no-tablespaces `
    --hex-blob --set-gtid-purged=OFF --default-character-set=utf8mb4 `
    "--result-file=$DumpPartial" $DbName
  if ($LASTEXITCODE -ne 0) { throw "mysqldump exited with $LASTEXITCODE. $DumpPartial is NOT a backup: leave it, record the failure, ask the DBA (variant B)." }
  'mysqldump exit code 0 — now run 4.5'
}
```

**Variant B — DBA account:** the same block with `-u <dba-account>` and
`--skip-routines --skip-events` replaced by `--routines --events`.

The dump is written under a `.partial` name. Only §4.5 renames it to `.sql`, after every
check passes, so a failed or interrupted dump can never carry the name of a valid backup.
Never rename a `.partial` file by hand.

### 4.5 Verify the dump [SAFE] / [WRITES FILE: renames, `.sha256`]

```powershell
. {
  # 1. Nothing wrote to the database between the baseline and the end of the dump
  Invoke-LmsSqlFile lms_migrator $DbName (Join-Path $VerifyDir 'table_content_hashes.sql') $AfterDumpRows
  $diff = @(Compare-Object (Get-Content -LiteralPath $BeforeRows) (Get-Content -LiteralPath $AfterDumpRows))
  if ($diff.Count) { $diff | Format-Table -AutoSize; throw 'Data changed during the backup window: an LMS writer is active. Stop it and restart from 4.0 with a new stamp.' }

  # 2. File present, plausible, not UTF-16 / BOM, complete
  $item = Get-Item -LiteralPath $DumpPartial
  if ($item.Length -lt 10KB) { throw "Dump is only $($item.Length) bytes" }
  $head = @(Get-Content -LiteralPath $DumpPartial -Encoding Byte -TotalCount 3)
  if (($head[0] -eq 0xFF -and $head[1] -eq 0xFE) -or ($head[0] -eq 0xFE -and $head[1] -eq 0xFF) -or ($head[0] -eq 0xEF -and $head[1] -eq 0xBB)) { throw 'Dump starts with a byte-order mark: not written by mysqldump --result-file' }
  $first = Get-Content -LiteralPath $DumpPartial -Encoding UTF8 -TotalCount 1
  $last  = Get-Content -LiteralPath $DumpPartial -Encoding UTF8 -Tail 1
  if ($first -notlike '-- MySQL dump *')       { throw "Unexpected first line: $first" }
  if ($last  -notlike '-- Dump completed on *') { throw "No completion marker; last line: $last" }

  # 3. Content and target checks
  function Get-DumpMatchCount([string]$Pattern) { @(Select-String -LiteralPath $DumpPartial -Pattern $Pattern -CaseSensitive -Encoding UTF8).Count }
  $snap = Get-Content -LiteralPath $Before -Raw -Encoding UTF8 | ConvertFrom-Json
  $checks = [ordered]@{
    'header names crescent_lms_dev'         = @((Get-DumpMatchCount '^-- Host: 127\.0\.0\.1\s+Database: crescent_lms_dev$'), 1)
    'SET NAMES utf8mb4'                     = @((Get-DumpMatchCount '^/\*!50503 SET NAMES utf8mb4 \*/;$'), 1)
    'CREATE TABLE statements'               = @((Get-DumpMatchCount '^CREATE TABLE `'), [int]$snap.table_count)
    'DROP TABLE IF EXISTS statements'       = @((Get-DumpMatchCount '^DROP TABLE IF EXISTS `'), [int]$snap.table_count)
    'USE / CREATE DATABASE / DROP DATABASE' = @((Get-DumpMatchCount '^(USE |CREATE DATABASE|DROP DATABASE)'), 0)
    'other lines naming crescent_lms_dev'   = @(@(Select-String -LiteralPath $DumpPartial -Pattern 'crescent_lms_dev' -CaseSensitive -Encoding UTF8 |
                                                  Where-Object { $_.Line -notmatch '^-- Host: ' -and $_.Line -notmatch '^INSERT INTO ' }).Count, 0)
    'audit triggers'                        = @((Get-DumpMatchCount 'TRIGGER `trg_audit_event_no_(update|delete)` BEFORE (UPDATE|DELETE) ON `audit_event`'), 2)
    'trigger DEFINER lms_migrator'          = @((Get-DumpMatchCount 'DEFINER=`lms_migrator`@`127\.0\.0\.1`'), 2)
    'alembic_version row 0010'              = @((Get-DumpMatchCount "^INSERT INTO ``alembic_version`` VALUES \('0010'\);$"), 1)
    'GTID statements'                       = @((Get-DumpMatchCount 'GTID_PURGED'), 0)
  }
  $bad = $false
  foreach ($k in $checks.Keys) { $v = $checks[$k]; $ok = $v[0] -eq $v[1]; if (-not $ok) { $bad = $true }
    '{0,-40} found {1,4}  expected {2,4}  {3}' -f $k, $v[0], $v[1], $(if ($ok) { 'OK' } else { 'FAIL' }) }
  $inserted = @(Select-String -LiteralPath $DumpPartial -Pattern '^INSERT INTO `([^`]+)`' -CaseSensitive -Encoding UTF8 |
                ForEach-Object { $_.Matches[0].Groups[1].Value } | Sort-Object -Unique)
  $nonEmpty = @($snap.row_counts.PSObject.Properties | Where-Object { $_.Value -gt 0 } | ForEach-Object { $_.Name } | Sort-Object)
  $tdiff = @(Compare-Object $nonEmpty $inserted)
  '{0,-40} found {1,4}  expected {2,4}  {3}' -f 'tables with INSERT = non-empty tables', $inserted.Count, $nonEmpty.Count, $(if ($tdiff.Count) { 'FAIL' } else { 'OK' })
  if ($tdiff.Count) { $tdiff; $bad = $true }
  if ($bad) { throw "Dump verification FAILED. $DumpPartial is not an accepted backup." }

  # 4. Accept: rename, checksum, protect
  Rename-Item -LiteralPath $DumpPartial -NewName (Split-Path -Leaf $Dump)
  $sha = (Get-FileHash -LiteralPath $Dump -Algorithm SHA256).Hash.ToLowerInvariant()
  "$sha  $(Split-Path -Leaf $Dump)" | Set-Content -LiteralPath $DumpSha -Encoding Ascii
  Set-ItemProperty -LiteralPath $Dump    -Name IsReadOnly -Value $true
  Set-ItemProperty -LiteralPath $DumpSha -Name IsReadOnly -Value $true
  "BACKUP ACCEPTED: $Dump  ($((Get-Item -LiteralPath $Dump).Length) bytes)  SHA256 $sha"
}
```

Expected: every line `OK`. Today, `tables with INSERT = non-empty tables` is 16, but the value
is taken from the snapshot, not hard-coded. Then `BACKUP ACCEPTED` with the size and SHA256.

**Retain together** in `C:\LMS_Backups`, and in the change record: `….sql`, `….sql.sha256`,
`….snapshot.json`, `….schema.txt`, `….rows.txt`, `….rows_after_dump.txt`, the stamp, the
SHA256 value, the DBA-gate result and (§5) the restore-test result. If a second copy is kept,
copy all of these files together to an access-controlled location approved by IT (not the
repository, not a synced OneDrive folder) and re-check the SHA256 there.

## 5. Restore test into a temporary database [DBA]

The DBA performs this, preferably before the upgrade and while the LMS is still stopped.
Nothing in this section touches `crescent_lms_dev`. It has **not been performed**:
no configured account can `CREATE DATABASE` (`lms_app` and `lms_migrator` are limited to
`crescent_lms_dev`, `lms_test` to `crescent_lms_test`).

**DBA account privileges needed:** `CREATE` (to create the database) and `DROP` on
`crescent_lms_restore_0011`. On that database: `SELECT, INSERT, CREATE, ALTER, INDEX,
REFERENCES, LOCK TABLES, TRIGGER`. Also `SET_USER_ID` or `SUPER`, because the dump's
triggers carry `DEFINER=lms_migrator@127.0.0.1`. That definer account exists; it has no
privileges on the temporary database, which does not matter because nothing fires the
triggers there. Do not test-fire them. The restore and the final `DROP DATABASE` are written
to the binary log (`log_bin = ON`). If this server has replicas, the DBA decides whether to
run the session with `sql_log_bin = 0`.

Name: `crescent_lms_restore_0011`. It differs from `crescent_lms_dev` and
`crescent_lms_test` and must not exist beforehand.

### 5.1 Preflight [DBA, read-only]

Open a new console, run §4.0 with `$Stamp` set to the recorded stamp, then:

```powershell
$DbaUser   = '<dba-account>'
$RestoreDb = 'crescent_lms_restore_0011'
. {
  if ($RestoreDb -in @('crescent_lms_dev', 'crescent_lms_test') -or $RestoreDb -notmatch '^crescent_lms_restore_[a-z0-9_]+$') { throw 'Invalid restore database name' }
  foreach ($f in $Dump, $DumpSha, $BeforeSchema, $BeforeRows) { if (-not (Test-Path -LiteralPath $f)) { throw "Missing $f" } }
  $expected = ((Get-Content -LiteralPath $DumpSha -TotalCount 1) -split '\s+')[0]
  $actual   = (Get-FileHash -LiteralPath $Dump -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($expected -ne $actual) { throw 'Dump SHA256 does not match the recorded value: do not restore' }
  $out = @(& $MySql -h $DbHost -P $DbPort -u $DbaUser -p --batch --skip-column-names -e "SELECT CONCAT_WS(' ', SCHEMA_NAME, DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME IN ('crescent_lms_dev', '$RestoreDb') ORDER BY SCHEMA_NAME")
  if ($LASTEXITCODE -ne 0) { throw "mysql.exe failed ($LASTEXITCODE)" }
  $out
  if ($out.Count -ne 1 -or $out[0] -ne 'crescent_lms_dev utf8mb4 utf8mb4_0900_ai_ci') { throw "$RestoreDb already exists or the source collation changed: stop" }
  & $MySql -h $DbHost -P $DbPort -u $DbaUser -p -e "SELECT CURRENT_USER(); SHOW GRANTS"
  if ($LASTEXITCODE -ne 0) { throw "mysql.exe failed ($LASTEXITCODE)" }
  'OK: dump hash matches, restore database absent, source is utf8mb4 / utf8mb4_0900_ai_ci'
}
```

Check the `SHOW GRANTS` output against the privilege list above.

The dump was already checked in §4.5 for `USE`, `CREATE DATABASE` and `DROP DATABASE`
(none) and for qualified references to `crescent_lms_dev` (none). Its statements therefore
apply only to the database chosen with `--database=` below.

### 5.2 Create and restore [DBA]

```powershell
. {
  # Plain CREATE DATABASE (no IF NOT EXISTS): fails, changing nothing, if the name is taken.
  & $MySql -h $DbHost -P $DbPort -u $DbaUser -p -e "CREATE DATABASE $RestoreDb CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
  if ($LASTEXITCODE -ne 0) { throw "CREATE DATABASE failed ($LASTEXITCODE): stop" }
  $src = $Dump -replace '\\', '/'
  & $MySql -h $DbHost -P $DbPort -u $DbaUser -p --default-character-set=utf8mb4 "--database=$RestoreDb" -e "source $src"
  if ($LASTEXITCODE -ne 0) { throw "Restore FAILED ($LASTEXITCODE): $RestoreDb is incomplete. Record the backup as NOT restore-tested; go to 5.4." }
  'Restore finished with exit code 0 — now run 5.3'
}
```

(`mysql.exe` stops at the first failing statement of a `source`d file and exits with 1;
verified with the 8.0.46 client.)

### 5.3 Verify the restored copy [DBA, read-only]

```powershell
. {
  $RestoreSchema = "$Base.restore.schema.txt"; $RestoreRows = "$Base.restore.rows.txt"
  Invoke-LmsSqlFile $DbaUser $RestoreDb (Join-Path $VerifyDir 'schema_fingerprint.sql')   $RestoreSchema
  Invoke-LmsSqlFile $DbaUser $RestoreDb (Join-Path $VerifyDir 'table_content_hashes.sql') $RestoreRows
  $s = @(Compare-Object (Get-Content -LiteralPath $BeforeSchema) (Get-Content -LiteralPath $RestoreSchema))
  $r = @(Compare-Object (Get-Content -LiteralPath $BeforeRows)   (Get-Content -LiteralPath $RestoreRows))
  $s | Format-Table -AutoSize -Wrap; $r | Format-Table -AutoSize -Wrap
  if ($s.Count -or $r.Count) { throw 'RESTORE TEST FAILED: the restored copy differs from crescent_lms_dev at backup time' }
  'RESTORE TEST PASSED'
}
```

What each comparison proves, line by line (a pass means zero differences):

| Check | Source of the line | Expected (restore vs. baseline) |
|---|---|---|
| Character set / collation of the database | `SCHEMA` | `SCHEMA utf8mb4 utf8mb4_0900_ai_ci` in both |
| Object counts | `COUNTS` | identical: 39 tables, 0 views, 419 columns, 187 indexes, 95 FKs, 37 CHECK, 57 UNIQUE, 2 triggers, 0 routines, 0 events |
| Engine, row format, table collation, column definitions (type, nullability, default, charset, collation, generated expression) | `TABLE … cols=` | identical for all 39 tables |
| Indexes (name, order, columns, uniqueness, prefix, visibility) | `TABLE … idx=` | identical |
| Foreign keys (name, columns, referenced table/column, rules) | `TABLE … fk=` | identical |
| CHECK constraints (name, clause, enforced) | `TABLE … chk=` | identical |
| Triggers (name, timing, event, body, definer, sql_mode, character sets) | `TABLE … trg=`, `TRIGGER` lines | identical, 2 triggers, definer `lms_migrator@127.0.0.1` |
| Row counts | `ROWS <table> <count>` | identical for all 39 tables |
| Table content | `ROWS … <content hash>` | identical for all 39 tables |
| Alembic revision | `alembic_version` content hash (and, if wanted, `SELECT version_num FROM crescent_lms_restore_0011.alembic_version` → `0010`) | identical / `0010` |

The content hash is the SHA-256 of the sorted per-row SHA-256 values, computed over every
column's value rendered as hex. It is independent of storage layout and row order, and
covers the `binary(16)`, `json` and generated columns. Like any hash it gives strong
evidence of equality, not a byte-for-byte proof. The restore test as a whole proves the
essential property: the file can be restored and reproduces the data and structure.
`CHECKSUM TABLE` (used by `db_readonly_snapshot.py`) is a weaker, layout-dependent
row-content checksum. Matching values are consistent with identical content but do not
prove a table is byte-identical, and they do not cover schema, indexes, constraints,
triggers or `AUTO_INCREMENT` counters. MySQL account grants and roles are server-level and
are not part of a single-database dump; §6 checks them separately.

### 5.4 Remove the temporary database [DBA] (drops only the temporary copy)

After recording the result (pass or fail), and only for this exact name:

```powershell
& $MySql -h $DbHost -P $DbPort -u $DbaUser -p -e "DROP DATABASE crescent_lms_restore_0011"
if ($LASTEXITCODE -ne 0) { "DROP failed ($LASTEXITCODE) — check manually" }
```

If no DBA account is available, record the backup as **verified but not restore-tested**.
The owner then decides whether that is sufficient before approving §6.

## 6. Upgrade and post-migration verification

### 6.1 Inspect the final SQL [SAFE]

```powershell
notepad ..\docs\database\migration-previews\0011_upgrade.sql
# or regenerate (offline, connects to nothing):
.venv\Scripts\python -m alembic upgrade 0010:0011 --sql | Out-File -Encoding utf8 -NoClobber (Join-Path $BackupDir "preview_0011_$Stamp.sql")
```

### 6.2 Apply — [MODIFIES DEV — APPROVAL REQUIRED]

> Run **only after the owner's explicit written approval**, with an accepted backup (§4.5),
> the restore-test result recorded (§5), the LMS still stopped (§4.2), and §4.3 re-run in
> this session (revision still `0010`).

```powershell
.venv\Scripts\python -m alembic upgrade 0011
if ($LASTEXITCODE -ne 0) { 'UPGRADE FAILED — do not start the LMS; follow section 8' }
```

### 6.3 Verify [SAFE] — run all four blocks before starting the LMS

**(a) Alembic revision**

```powershell
.venv\Scripts\python -m alembic current     # expect exactly: 0011 (head)
```

**(b) Snapshot comparison** (runtime account: row counts, `CHECKSUM TABLE`, 0011 grants)

```powershell
.venv\Scripts\python ..\scripts\db_readonly_snapshot.py --compare $Before
```

Expected output, exactly (the `30 -> 36` / `75 -> 87` values hold if the counts at backup
time were 30 and 75 as on 2026-11-23; in general they are `+6` and `+12`):

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

Note: `triggers unchanged: True` is **not** a trigger check. The runtime account cannot see
triggers, so both lists are empty; (c) verifies triggers.

**(c) Structure and content comparison** (migration account)

```powershell
. {
  $AfterSchema = "$Base.after_0011.schema.txt"; $AfterRows = "$Base.after_0011.rows.txt"
  Invoke-LmsSqlFile lms_migrator $DbName (Join-Path $VerifyDir 'schema_fingerprint.sql')   $AfterSchema
  Invoke-LmsSqlFile lms_migrator $DbName (Join-Path $VerifyDir 'table_content_hashes.sql') $AfterRows
  Compare-Object (Get-Content -LiteralPath $BeforeSchema) (Get-Content -LiteralPath $AfterSchema) | Format-Table -AutoSize -Wrap
  Compare-Object (Get-Content -LiteralPath $BeforeRows)   (Get-Content -LiteralPath $AfterRows)   | Format-Table -AutoSize -Wrap
}
```

Expected `schema` differences, and **no others** (`=>` = only after, `<=` = only before):

| Side | Line |
|---|---|
| `<=` | `COUNTS tables=39 views=0 columns=419 indexes=187 foreign_keys=95 checks=37 uniques=57 triggers=2 routines=0 events=0` |
| `=>` | `COUNTS tables=54 views=0 columns=620 indexes=286 foreign_keys=148 checks=65 uniques=81 triggers=2 routines=0 events=0` |
| `=>` | 15 `TABLE` lines, one per new table, exactly as below |

```text
TABLE competency InnoDB Dynamic utf8mb4_0900_ai_ci cols=986a0a3450d33b2e idx=5e170aede0579105 fk=7c6119eaa332b30f chk=e69fb552bd70d000 trg=none
TABLE competency_assessment InnoDB Dynamic utf8mb4_0900_ai_ci cols=d8d572141fefb73b idx=235279b9ab1c515a fk=9156588270692d5b chk=f444c04e46a571d6 trg=none
TABLE competency_band_requirement InnoDB Dynamic utf8mb4_0900_ai_ci cols=f4c58002f1fab191 idx=31409ad44cf8c823 fk=9e6d76a9c73648e5 chk=none trg=none
TABLE competency_level_descriptor InnoDB Dynamic utf8mb4_0900_ai_ci cols=d9d5f33c2fec207f idx=d6ec24b7596833ac fk=8b4b905f2ff14a41 chk=none trg=none
TABLE notification InnoDB Dynamic utf8mb4_0900_ai_ci cols=20d674527c008cf3 idx=8400e1603476776a fk=52882a6934711879 chk=none trg=none
TABLE notification_preference InnoDB Dynamic utf8mb4_0900_ai_ci cols=3fc6489c8f49c3d3 idx=ef70d0983c23a9ac fk=c286fbe381f3be45 chk=none trg=none
TABLE proficiency_level InnoDB Dynamic utf8mb4_0900_ai_ci cols=a65f5a73cf730dc9 idx=f5bb621e7c27eb65 fk=2f241b7255656378 chk=556fbc3ff69f96c7 trg=none
TABLE proficiency_scale InnoDB Dynamic utf8mb4_0900_ai_ci cols=e190004aafbb08d1 idx=fafbbaf5d26a56a4 fk=dbda1802b8f6b8ad chk=3bc141edb2fb7bd1 trg=none
TABLE skill_matrix InnoDB Dynamic utf8mb4_0900_ai_ci cols=82f5a999f2d93d7d idx=3def3455f9207067 fk=007f9fbfb1728096 chk=none trg=none
TABLE skill_matrix_item InnoDB Dynamic utf8mb4_0900_ai_ci cols=a3177f5e73c8a144 idx=ed8ee4fdc21b8889 fk=89753fc7e00b88df chk=none trg=none
TABLE skill_matrix_member InnoDB Dynamic utf8mb4_0900_ai_ci cols=96c650e7b76d70fe idx=a1e49bd5bd4c9a19 fk=4cfc24ca49bd3b9a chk=none trg=none
TABLE training_event InnoDB Dynamic utf8mb4_0900_ai_ci cols=243baa2519dbbb6a idx=e5beb497ca529b10 fk=aeeb29e30342c5b6 chk=6cb799e748b46a0d trg=none
TABLE training_participation InnoDB Dynamic utf8mb4_0900_ai_ci cols=e8562eb259d307f8 idx=84d848eb179c98a6 fk=464044c78615c6fb chk=e16414af06a3a5c0 trg=none
TABLE training_programme InnoDB Dynamic utf8mb4_0900_ai_ci cols=612ceecf0ff5a50a idx=f4b7346fde71f138 fk=195e83c929d8d945 chk=31b0a7b7d66cd524 trg=none
TABLE training_session InnoDB Dynamic utf8mb4_0900_ai_ci cols=9cba4827c3477a2a idx=29e566f7ac58c6ea fk=cf0773c46d11290f chk=239b23d410ac63ea trg=none
```

These values were measured on `crescent_lms_test` after the rehearsed upgrade to 0011. The
same file shows the 38 other pre-existing tables there with fingerprints identical to
`crescent_lms_dev` today. `audit_event` differs only in its trigger definer
(`lms_test@127.0.0.1` there). Consequently: **no `SCHEMA`, `TRIGGER` or pre-existing
`TABLE` line may differ.** A pre-existing `TABLE` line that differs means an existing table's
structure changed. A differing `TRIGGER` line means a trigger changed. Either case: stop and
go to §8. A new-table line that differs from the list above is not by itself data damage,
but it is unexpected; investigate before starting the LMS.

Expected `rows` differences, and **no others**:

| Side | Line(s) |
|---|---|
| `<=` / `=>` | `ROWS access_permission 30 …` → `ROWS access_permission 36 …` (+6, new hash) |
| `<=` / `=>` | `ROWS access_role_permission 75 …` → `ROWS access_role_permission 87 …` (+12, new hash) |
| `<=` / `=>` | `ROWS alembic_version 1 …` → `ROWS alembic_version 1 …` (new hash: value `0010` → `0011`) |
| `=>` | `ROWS proficiency_level 9 <hash>` and `ROWS proficiency_scale 2 <hash>` (hashes vary: generated ids and timestamps) |
| `=>` | `ROWS <table> 0 empty` for the other 13 new tables |

The remaining 36 pre-existing tables must have **identical** `ROWS` lines (same count, same
content hash). Any other difference means existing data was affected: stop and go to §8.

**(d) Application permissions and MySQL account grants**

```powershell
& $MySql -h $DbHost -P $DbPort -u lms_migrator -p --table "--database=$DbName" -e "SELECT r.code AS role, p.code AS permission, p.is_privileged FROM access_role_permission m JOIN access_role r ON r.id = m.access_role_id JOIN access_permission p ON p.id = m.access_permission_id WHERE p.code IN ('training.records.view','competency.view','competency.manage','competency.assess','imports.organisation.run','imports.organisation.commit') ORDER BY r.code, p.code; SELECT r.code AS role, COUNT(*) AS grants FROM access_role r LEFT JOIN access_role_permission m ON m.access_role_id = r.id GROUP BY r.code ORDER BY r.code; SELECT COUNT(*) AS permissions FROM access_permission; SHOW GRANTS"
```

Expected:

* 12 rows: `hr_admin` and `super_admin`, each with `competency.assess`, `competency.manage`,
  `competency.view`, `imports.organisation.commit`, `imports.organisation.run`,
  `training.records.view`, all `is_privileged = 0`.
* Grants per role: `employee 3`, `hod 5`, `hr_admin 33` (was 27), `sme 5`,
  `super_admin 36` (was 30), `supervisor 5`.
* `permissions 36`.
* `SHOW GRANTS` unchanged:
  `GRANT USAGE ON *.* TO lms_migrator@127.0.0.1` and
  `GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, REFERENCES, INDEX, ALTER, TRIGGER ON crescent_lms_dev.* TO lms_migrator@127.0.0.1`.
  Optionally, the same `SHOW GRANTS` as `lms_app` must still read `USAGE` plus
  `SELECT, INSERT, UPDATE, DELETE ON crescent_lms_dev.*`.

## 7. Start the application and smoke test [SAFE]

Only after §6.3 (a)–(d) match.

```powershell
$env:LMS_TRUSTED_ORIGINS = 'http://localhost:4180,http://127.0.0.1:4180,http://localhost:5173,http://127.0.0.1:5173'
.venv\Scripts\python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8010 --reload --reload-dir app --log-level warning
```

- `http://127.0.0.1:8010/api/v1/health/ready` → `ready`.
- Sign in at `http://127.0.0.1:4180` as an HR Admin / Super Admin: Training register,
  Calendar, Skill matrix, Competency library and Notifications open **without** the
  "awaiting database update" notice; Competency library → Proficiency scales lists the
  two seeded scales; Notifications → channels shows Outlook/Teams *not connected*.
- `.venv\Scripts\python -m app.jobs training-reminders --dry-run` → `Dry run: 0 reminder(s)…`.
- Re-enable any scheduled task disabled in §4.2. Optional: schedule the reminder job
  (README, "Scheduled job").

## 8. Rollback [DBA] — needs explicit approval

Preferred: restore the §4 backup. Restoring the dump over a migrated database is **not**
sufficient on its own. The dump drops and recreates only the 39 tables it contains; it
would leave the 15 tables created by 0011 in place, still referencing the recreated tables.
The pre-flight would then refuse a later re-run. `lms_migrator` also cannot restore the
dump (no `LOCK TABLES`). The DBA therefore, with the LMS stopped:

1. verifies the dump against its `.sha256` (as in §5.1);
2. drops exactly the 0011 tables that exist (in one session with
   `SET FOREIGN_KEY_CHECKS = 0`): `notification_preference`, `proficiency_scale`,
   `proficiency_level`, `competency`, `competency_band_requirement`,
   `competency_level_descriptor`, `skill_matrix`, `training_programme`,
   `competency_assessment`, `skill_matrix_item`, `skill_matrix_member`, `training_event`,
   `notification`, `training_participation`, `training_session`;
3. restores with `mysql.exe … --default-character-set=utf8mb4 --database=crescent_lms_dev -e "source <dump>"`
   and checks the exit code;
4. runs §6.3 (c) against `crescent_lms_dev` with new output names and compares with
   `$BeforeSchema` / `$BeforeRows`. Expected: **no differences** (and `alembic current` → `0010`).

`alembic downgrade 0010` is possible only while the new tables are empty and the seeds
unchanged (the guard refuses otherwise), and also needs explicit approval.

## 9. Rehearsal and validation record

* **2026-11-23, `crescent_lms_test` only:** backup with `mysqldump`, integrity checks, drop
  every table, restore from the dump, compare row counts and `CHECKSUM TABLE` values,
  upgrade to 0011, verify existing tables unchanged, downgrade, rebuild (see the review
  report for the run output).
* **2026-11-23, this re-validation, read-only on `crescent_lms_dev`:**
  * grants of both accounts, schema facts and object counts (§3);
  * `db_readonly_snapshot.py` piped through `Out-File -Encoding utf8` (BOM), read back by
    `--compare` with no `CHANGED` lines;
  * both verification SQL files run through `mysql.exe` against `crescent_lms_dev` (as
    `lms_migrator`) and `crescent_lms_test` (as `lms_test`);
  * `mysql.exe` confirmed to exit 1 on an error inside a `source`d file;
  * the §4.4 / §4.5 PowerShell blocks run end-to-end against `crescent_lms_test`, into a
    scratch folder, to validate the commands, exit-code gates and dump checks.

  No dump of `crescent_lms_dev` was taken, and nothing was restored, created or dropped.
* **Not yet performed:** the `crescent_lms_dev` backup (§4), the DBA gate (§4.3), the DBA
  restore test (§5), the upgrade (§6).
