PRAGMA foreign_keys = OFF;

-- Rename legacy domain-specific context columns to neutral names.
ALTER TABLE research_events RENAME COLUMN study_stage TO stage;
ALTER TABLE research_events RENAME COLUMN biological_system TO system_context;
ALTER TABLE research_events RENAME COLUMN application_area TO application_context;

PRAGMA foreign_keys = ON;
