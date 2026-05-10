-- Add structured fact extraction and temporal conflict resolution tables
-- Phase 1 of the Personal Knowledge Graph architecture

-- 1. facts table: canonical persistent claims about the user
CREATE TABLE IF NOT EXISTS facts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  entity_key TEXT NOT NULL,
  entity_category TEXT NOT NULL,
  value TEXT NOT NULL,
  confidence FLOAT NOT NULL,
  tense TEXT NOT NULL DEFAULT 'present',
  first_seen_at TIMESTAMP WITH TIME ZONE NOT NULL,
  last_confirmed_at TIMESTAMP WITH TIME ZONE NOT NULL,
  superseded_at TIMESTAMP WITH TIME ZONE,
  is_current BOOLEAN NOT NULL DEFAULT true,
  source_chunk_ids TEXT[] NOT NULL DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX IF NOT EXISTS facts_user_current ON facts(user_id, is_current);
CREATE INDEX IF NOT EXISTS facts_entity ON facts(user_id, entity_key, entity_category);
CREATE INDEX IF NOT EXISTS facts_category ON facts(entity_category);

-- Enable Row Level Security
ALTER TABLE facts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own facts" ON facts;
DROP POLICY IF EXISTS "Users can insert own facts" ON facts;
DROP POLICY IF EXISTS "Users can update own facts" ON facts;
DROP POLICY IF EXISTS "Users can delete own facts" ON facts;

CREATE POLICY "Users can view own facts"
  ON facts FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own facts"
  ON facts FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own facts"
  ON facts FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own facts"
  ON facts FOR DELETE
  USING (auth.uid() = user_id);

-- 2. candidate_facts table: staging area for low-confidence or unconfirmed claims
CREATE TABLE IF NOT EXISTS candidate_facts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  entity_key TEXT NOT NULL,
  entity_category TEXT NOT NULL,
  value TEXT NOT NULL,
  confidence FLOAT NOT NULL,
  tense TEXT NOT NULL DEFAULT 'present',
  source_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  source_chunk_ids TEXT[] NOT NULL DEFAULT '{}',
  confirmation_count INT NOT NULL DEFAULT 1,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX IF NOT EXISTS candidate_facts_user ON candidate_facts(user_id);
CREATE INDEX IF NOT EXISTS candidate_facts_entity ON candidate_facts(user_id, entity_key, entity_category);

-- Enable Row Level Security
ALTER TABLE candidate_facts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own candidate facts" ON candidate_facts;
DROP POLICY IF EXISTS "Users can insert own candidate facts" ON candidate_facts;
DROP POLICY IF EXISTS "Users can update own candidate facts" ON candidate_facts;
DROP POLICY IF EXISTS "Users can delete own candidate facts" ON candidate_facts;

CREATE POLICY "Users can view own candidate facts"
  ON candidate_facts FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own candidate facts"
  ON candidate_facts FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own candidate facts"
  ON candidate_facts FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own candidate facts"
  ON candidate_facts FOR DELETE
  USING (auth.uid() = user_id);

-- 3. fact_changes table: audit log of supersessions (the timeline)
CREATE TABLE IF NOT EXISTS fact_changes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  old_fact_id UUID REFERENCES facts(id) ON DELETE SET NULL,
  new_fact_id UUID REFERENCES facts(id) ON DELETE SET NULL,
  entity_key TEXT NOT NULL,
  entity_category TEXT NOT NULL,
  old_value TEXT,
  new_value TEXT NOT NULL,
  detected_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  source_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  confidence FLOAT NOT NULL,
  detection_reason TEXT NOT NULL,
  is_reversion BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX IF NOT EXISTS fact_changes_user_timeline ON fact_changes(user_id, source_timestamp DESC);
CREATE INDEX IF NOT EXISTS fact_changes_entity ON fact_changes(user_id, entity_key);
CREATE INDEX IF NOT EXISTS fact_changes_category ON fact_changes(entity_category);

-- Enable Row Level Security
ALTER TABLE fact_changes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own fact changes" ON fact_changes;
DROP POLICY IF EXISTS "Users can insert own fact changes" ON fact_changes;
DROP POLICY IF EXISTS "Users can update own fact changes" ON fact_changes;
DROP POLICY IF EXISTS "Users can delete own fact changes" ON fact_changes;

CREATE POLICY "Users can view own fact changes"
  ON fact_changes FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own fact changes"
  ON fact_changes FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own fact changes"
  ON fact_changes FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own fact changes"
  ON fact_changes FOR DELETE
  USING (auth.uid() = user_id);

-- 4. Triggers for updated_at columns
DROP TRIGGER IF EXISTS update_facts_updated_at ON facts;
CREATE TRIGGER update_facts_updated_at
    BEFORE UPDATE ON facts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_candidate_facts_updated_at ON candidate_facts;
CREATE TRIGGER update_candidate_facts_updated_at
    BEFORE UPDATE ON candidate_facts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_fact_changes_updated_at ON fact_changes;
CREATE TRIGGER update_fact_changes_updated_at
    BEFORE UPDATE ON fact_changes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 5. RPC helper: append a source_chunk_id to a fact's source_chunk_ids array
CREATE OR REPLACE FUNCTION append_fact_source_chunk(fact_id UUID, chunk_id TEXT)
RETURNS void AS $$
BEGIN
  UPDATE facts
  SET source_chunk_ids = array_append(source_chunk_ids, chunk_id)
  WHERE id = fact_id AND NOT (chunk_id = ANY(source_chunk_ids));
END;
$$ LANGUAGE plpgsql;

-- 6. RPC helper: get timeline for a user with optional category filter
CREATE OR REPLACE FUNCTION get_user_timeline(
  p_user_id UUID,
  p_category TEXT DEFAULT NULL,
  p_limit INT DEFAULT 50
)
RETURNS TABLE (
  id UUID,
  entity_key TEXT,
  entity_category TEXT,
  old_value TEXT,
  new_value TEXT,
  source_timestamp TIMESTAMP WITH TIME ZONE,
  confidence FLOAT,
  detection_reason TEXT,
  is_reversion BOOLEAN,
  detected_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
  RETURN QUERY
  SELECT fc.id, fc.entity_key, fc.entity_category, fc.old_value, fc.new_value,
         fc.source_timestamp, fc.confidence, fc.detection_reason, fc.is_reversion, fc.detected_at
  FROM fact_changes fc
  WHERE fc.user_id = p_user_id
    AND (p_category IS NULL OR fc.entity_category = p_category)
  ORDER BY fc.source_timestamp DESC
  LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;
