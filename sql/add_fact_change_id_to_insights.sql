-- Add fact_change_id foreign key to user_insights to prevent duplicate cards
-- This ensures each fact change generates at most one insight card

-- Add the foreign key column
ALTER TABLE user_insights 
ADD COLUMN IF NOT EXISTS fact_change_id UUID REFERENCES fact_changes(id) ON DELETE SET NULL;

-- Create unique constraint to prevent duplicate insight cards from the same fact change
ALTER TABLE user_insights 
ADD CONSTRAINT user_insights_unique_fact_change 
UNIQUE (user_id, fact_change_id);

-- Create index for faster lookups by fact_change_id
CREATE INDEX IF NOT EXISTS idx_user_insights_fact_change_id ON user_insights(fact_change_id);

-- Add a partial index for insights that came from fact changes (vs other sources)
CREATE INDEX idx_user_insights_from_fact_changes ON user_insights(user_id) 
WHERE fact_change_id IS NOT NULL;
