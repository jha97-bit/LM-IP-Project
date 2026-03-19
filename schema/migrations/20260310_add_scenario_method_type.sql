ALTER TABLE scenarios
ADD COLUMN IF NOT EXISTS method_type text;

UPDATE scenarios
SET method_type = 'topsis'
WHERE method_type IS NULL;

ALTER TABLE scenarios
ALTER COLUMN method_type SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'scenarios_method_type_check'
    ) THEN
        ALTER TABLE scenarios
        ADD CONSTRAINT scenarios_method_type_check
        CHECK (method_type IN ('topsis', 'vft'));
    END IF;
END $$;
