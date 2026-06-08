-- Migration rollback / recovery notes:
-- If the copy verification below fails, the script aborts before dropping quantitative_measurements_old.
-- Re-enable foreign keys with PRAGMA foreign_keys = ON after rolling back or rerunning the migration.
-- The transaction should remain intact until the row-count check passes.
-- If the INSERT or verification fails, rerun the migration after fixing the source data and re-enabling foreign keys.

PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

ALTER TABLE quantitative_measurements RENAME TO quantitative_measurements_old;

CREATE TABLE quantitative_measurements (
  measurement_id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL,
  measurement_type TEXT NOT NULL,
  value TEXT NOT NULL,
  unit TEXT NOT NULL,
  context TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (event_id) REFERENCES research_events(event_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_quantitative_measurements_event_id
ON quantitative_measurements(event_id);

CREATE INDEX IF NOT EXISTS idx_measurements_type
ON quantitative_measurements(measurement_type);

INSERT INTO quantitative_measurements (
  measurement_id,
  event_id,
  measurement_type,
  value,
  unit,
  context,
  created_at
)
SELECT
  measurement_id,
  event_id,
  measurement_type,
  CAST(value AS TEXT),
  unit,
  context,
  created_at
FROM quantitative_measurements_old;

-- Verify that the copy preserved every row before removing the old table.
CREATE TEMP TABLE migration_verification (
  pass INTEGER NOT NULL CHECK (pass = 1)
);

INSERT INTO migration_verification (pass)
SELECT CASE
  WHEN (
    SELECT COUNT(*) FROM quantitative_measurements
  ) = (
    SELECT COUNT(*) FROM quantitative_measurements_old
  ) THEN 1
  ELSE 0
END;

DROP TABLE migration_verification;

DROP TABLE quantitative_measurements_old;

COMMIT;

PRAGMA foreign_keys = ON;