-- Rename legacy research_events context columns to the current schema names.
-- Run this only on databases that still use the legacy column names.

ALTER TABLE research_events RENAME COLUMN biological_system TO system_context;
ALTER TABLE research_events RENAME COLUMN application_area TO application_context;
