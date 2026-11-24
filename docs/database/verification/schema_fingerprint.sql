-- Read-only structural fingerprint of the CURRENT database (DATABASE()).
--
-- Part of the migration 0011 approval package (docs/database/MIGRATION_0011_APPROVAL_PACKAGE.md).
-- Issues SELECT statements only, inside a READ ONLY transaction, then rolls back.
-- Run with:  mysql --batch --skip-column-names --raw --database=<schema> -e "source <this file>"
--
-- Output, one line each:
--   SCHEMA   <default charset> <default collation>
--   COUNTS   tables= views= columns= indexes= foreign_keys= checks= uniques= triggers= routines= events=
--   TABLE    <name> <engine> <row format> <collation> cols=<h> idx=<h> fk=<h> chk=<h> trg=<h>
--   TRIGGER  <name> <table> <timing> <event> <definer>
-- <h> = first 16 hex chars of SHA-256 over that table's column / index / foreign-key /
-- check-constraint / trigger definitions ("none" when the table has none). Two outputs are
-- compared line by line (Compare-Object); the hashes only show WHICH category differs —
-- inspect information_schema for the detail.
--
-- Visibility: routines and events are listed only for accounts holding a routine privilege
-- (EXECUTE / SHOW_ROUTINE / global SELECT) or EVENT. For lms_migrator those two counts are
-- therefore NOT proof that none exist; a DBA account gives authoritative values.

START TRANSACTION READ ONLY;
SET SESSION group_concat_max_len = 16777216;

SELECT CONCAT_WS(' ', 'SCHEMA', DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME)
FROM information_schema.SCHEMATA
WHERE SCHEMA_NAME = DATABASE();

SELECT CONCAT_WS(' ', 'COUNTS',
  CONCAT('tables=', (SELECT COUNT(*) FROM information_schema.TABLES
                     WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE')),
  CONCAT('views=', (SELECT COUNT(*) FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'VIEW')),
  CONCAT('columns=', (SELECT COUNT(*) FROM information_schema.COLUMNS
                      WHERE TABLE_SCHEMA = DATABASE())),
  CONCAT('indexes=', (SELECT COUNT(*) FROM (SELECT DISTINCT TABLE_NAME, INDEX_NAME
                      FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE()) i)),
  CONCAT('foreign_keys=', (SELECT COUNT(*) FROM information_schema.REFERENTIAL_CONSTRAINTS
                           WHERE CONSTRAINT_SCHEMA = DATABASE())),
  CONCAT('checks=', (SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
                     WHERE CONSTRAINT_SCHEMA = DATABASE() AND CONSTRAINT_TYPE = 'CHECK')),
  CONCAT('uniques=', (SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
                      WHERE CONSTRAINT_SCHEMA = DATABASE() AND CONSTRAINT_TYPE = 'UNIQUE')),
  CONCAT('triggers=', (SELECT COUNT(*) FROM information_schema.TRIGGERS
                       WHERE TRIGGER_SCHEMA = DATABASE())),
  CONCAT('routines=', (SELECT COUNT(*) FROM information_schema.ROUTINES
                       WHERE ROUTINE_SCHEMA = DATABASE())),
  CONCAT('events=', (SELECT COUNT(*) FROM information_schema.EVENTS
                     WHERE EVENT_SCHEMA = DATABASE())));

SELECT CONCAT_WS(' ', 'TABLE', t.TABLE_NAME, t.ENGINE, t.ROW_FORMAT, t.TABLE_COLLATION,
  CONCAT('cols=', IFNULL(LEFT(SHA2((
    SELECT GROUP_CONCAT(CONCAT_WS('|', c.ORDINAL_POSITION, c.COLUMN_NAME, c.COLUMN_TYPE,
             c.IS_NULLABLE, IFNULL(c.COLUMN_DEFAULT, '<null>'), IFNULL(c.CHARACTER_SET_NAME, '-'),
             IFNULL(c.COLLATION_NAME, '-'), c.EXTRA, c.GENERATION_EXPRESSION)
           ORDER BY c.ORDINAL_POSITION SEPARATOR '\n')
    FROM information_schema.COLUMNS c
    WHERE c.TABLE_SCHEMA = t.TABLE_SCHEMA AND c.TABLE_NAME = t.TABLE_NAME), 256), 16), 'none')),
  CONCAT('idx=', IFNULL(LEFT(SHA2((
    SELECT GROUP_CONCAT(CONCAT_WS('|', s.INDEX_NAME, s.SEQ_IN_INDEX, IFNULL(s.COLUMN_NAME, '-'),
             s.NON_UNIQUE, IFNULL(s.SUB_PART, '-'), s.INDEX_TYPE, s.IS_VISIBLE,
             IFNULL(s.EXPRESSION, '-'), IFNULL(s.COLLATION, '-'))
           ORDER BY s.INDEX_NAME, s.SEQ_IN_INDEX SEPARATOR '\n')
    FROM information_schema.STATISTICS s
    WHERE s.TABLE_SCHEMA = t.TABLE_SCHEMA AND s.TABLE_NAME = t.TABLE_NAME), 256), 16), 'none')),
  CONCAT('fk=', IFNULL(LEFT(SHA2((
    SELECT GROUP_CONCAT(CONCAT_WS('|', k.CONSTRAINT_NAME, k.ORDINAL_POSITION, k.COLUMN_NAME,
             IF(k.REFERENCED_TABLE_SCHEMA = k.TABLE_SCHEMA, 'same-schema', k.REFERENCED_TABLE_SCHEMA),
             k.REFERENCED_TABLE_NAME, k.REFERENCED_COLUMN_NAME, r.UPDATE_RULE, r.DELETE_RULE)
           ORDER BY k.CONSTRAINT_NAME, k.ORDINAL_POSITION SEPARATOR '\n')
    FROM information_schema.KEY_COLUMN_USAGE k
    JOIN information_schema.REFERENTIAL_CONSTRAINTS r
      ON r.CONSTRAINT_SCHEMA = k.CONSTRAINT_SCHEMA AND r.CONSTRAINT_NAME = k.CONSTRAINT_NAME
     AND r.TABLE_NAME = k.TABLE_NAME
    WHERE k.TABLE_SCHEMA = t.TABLE_SCHEMA AND k.TABLE_NAME = t.TABLE_NAME
      AND k.REFERENCED_TABLE_NAME IS NOT NULL), 256), 16), 'none')),
  CONCAT('chk=', IFNULL(LEFT(SHA2((
    SELECT GROUP_CONCAT(CONCAT_WS('|', tc.CONSTRAINT_NAME, tc.ENFORCED, cc.CHECK_CLAUSE)
           ORDER BY tc.CONSTRAINT_NAME SEPARATOR '\n')
    FROM information_schema.TABLE_CONSTRAINTS tc
    JOIN information_schema.CHECK_CONSTRAINTS cc
      ON cc.CONSTRAINT_SCHEMA = tc.CONSTRAINT_SCHEMA AND cc.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
    WHERE tc.TABLE_SCHEMA = t.TABLE_SCHEMA AND tc.TABLE_NAME = t.TABLE_NAME
      AND tc.CONSTRAINT_TYPE = 'CHECK'), 256), 16), 'none')),
  CONCAT('trg=', IFNULL(LEFT(SHA2((
    SELECT GROUP_CONCAT(CONCAT_WS('|', g.TRIGGER_NAME, g.ACTION_TIMING, g.EVENT_MANIPULATION,
             g.ACTION_ORDER, g.ACTION_STATEMENT, g.DEFINER, g.SQL_MODE, g.CHARACTER_SET_CLIENT,
             g.COLLATION_CONNECTION, g.DATABASE_COLLATION)
           ORDER BY g.TRIGGER_NAME SEPARATOR '\n')
    FROM information_schema.TRIGGERS g
    WHERE g.EVENT_OBJECT_SCHEMA = t.TABLE_SCHEMA AND g.EVENT_OBJECT_TABLE = t.TABLE_NAME), 256), 16), 'none')))
FROM information_schema.TABLES t
WHERE t.TABLE_SCHEMA = DATABASE() AND t.TABLE_TYPE = 'BASE TABLE'
ORDER BY t.TABLE_NAME;

SELECT CONCAT_WS(' ', 'TRIGGER', TRIGGER_NAME, EVENT_OBJECT_TABLE, ACTION_TIMING,
                 EVENT_MANIPULATION, DEFINER)
FROM information_schema.TRIGGERS
WHERE TRIGGER_SCHEMA = DATABASE()
ORDER BY TRIGGER_NAME;

ROLLBACK;
