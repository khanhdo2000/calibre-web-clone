-- Migration: Add display_order to categories table
-- This can be run directly on your production PostgreSQL database

BEGIN;

-- Add display_order column (nullable first)
ALTER TABLE categories ADD COLUMN IF NOT EXISTS display_order INTEGER;

-- Set default values based on current id order
UPDATE categories
SET display_order = id * 10
WHERE display_order IS NULL;

-- Make it NOT NULL now that all rows have values
ALTER TABLE categories ALTER COLUMN display_order SET NOT NULL;
ALTER TABLE categories ALTER COLUMN display_order SET DEFAULT 0;

-- Add index for better query performance
CREATE INDEX IF NOT EXISTS ix_categories_display_order ON categories(display_order);

-- Verify the changes
SELECT id, name, display_order FROM categories ORDER BY display_order;

COMMIT;
