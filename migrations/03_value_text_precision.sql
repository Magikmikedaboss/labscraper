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

DROP TABLE quantitative_measurements_old;

COMMIT;

PRAGMA foreign_keys = ON;