-- Read-only per-table row count and content hash of the CURRENT database (DATABASE()).
--
-- Part of the migration 0011 approval package (docs/database/MIGRATION_0011_APPROVAL_PACKAGE.md).
-- Issues SELECT statements only (one generated, prepared SELECT), inside a
-- READ ONLY consistent-snapshot transaction, then rolls back. Creates no stored objects.
-- Run with:  mysql --batch --skip-column-names --raw --database=<schema> -e "source <this file>"
--
-- Output, one line per base table:
--   ROWS <table> <row count> <content hash>
-- Content hash: every row is rendered as the hex of each column's value
-- (CAST(... AS BINARY); NULL rendered distinctly), SHA-256 per row, the row hashes sorted and
-- concatenated, SHA-256 of that ("empty" for an empty table). It is independent of physical
-- row order and storage layout, covers every column including binary(16), JSON and stored
-- generated columns, and differs if any value in any row differs. Like any hash it is strong
-- evidence, not a byte-for-byte proof; it does not cover schema, AUTO_INCREMENT counters or
-- triggers (see schema_fingerprint.sql).

START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY;
SET SESSION group_concat_max_len = 1073741824;

SET @lms_hash_sql = (
  SELECT GROUP_CONCAT(
    CONCAT(
      'SELECT ', QUOTE(t.TABLE_NAME), ' AS table_name, COUNT(*) AS row_count, ',
      'IFNULL(SHA2(GROUP_CONCAT(h ORDER BY h SEPARATOR ''''), 256), ''empty'') AS content_hash ',
      'FROM (SELECT SHA2(CONCAT_WS(''|'', ',
      (SELECT GROUP_CONCAT(
                CONCAT('IFNULL(HEX(CAST(`', c.COLUMN_NAME, '` AS BINARY)), ''N'')')
                ORDER BY c.ORDINAL_POSITION SEPARATOR ', ')
       FROM information_schema.COLUMNS c
       WHERE c.TABLE_SCHEMA = t.TABLE_SCHEMA AND c.TABLE_NAME = t.TABLE_NAME),
      '), 256) AS h FROM `', t.TABLE_NAME, '`) x')
    ORDER BY t.TABLE_NAME SEPARATOR ' UNION ALL ')
  FROM information_schema.TABLES t
  WHERE t.TABLE_SCHEMA = DATABASE() AND t.TABLE_TYPE = 'BASE TABLE');

SET @lms_hash_sql = CONCAT(
  'SELECT CONCAT_WS('' '', ''ROWS'', table_name, row_count, content_hash) FROM (',
  @lms_hash_sql, ') z ORDER BY table_name');

PREPARE lms_hash_stmt FROM @lms_hash_sql;
EXECUTE lms_hash_stmt;
DEALLOCATE PREPARE lms_hash_stmt;

ROLLBACK;
