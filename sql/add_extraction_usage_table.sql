-- Add extraction_usage table for daily LLM call budget tracking
CREATE TABLE IF NOT EXISTS extraction_usage (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  calls_used INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(user_id, date)
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_extraction_usage_user_date ON extraction_usage(user_id, date);

-- Enable Row Level Security
ALTER TABLE extraction_usage ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view own extraction usage" ON extraction_usage;
DROP POLICY IF EXISTS "Users can insert own extraction usage" ON extraction_usage;
DROP POLICY IF EXISTS "Users can update own extraction usage" ON extraction_usage;

-- Policy: Users can only see their own usage
CREATE POLICY "Users can view own extraction usage"
  ON extraction_usage FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own extraction usage"
  ON extraction_usage FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own extraction usage"
  ON extraction_usage FOR UPDATE
  USING (auth.uid() = user_id);

-- Create trigger for updated_at timestamp
DROP TRIGGER IF EXISTS update_extraction_usage_updated_at ON extraction_usage;
CREATE TRIGGER update_extraction_usage_updated_at
    BEFORE UPDATE ON extraction_usage
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add feature_flags table for gradual rollout control
CREATE TABLE IF NOT EXISTS feature_flags (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  flag_name TEXT NOT NULL,
  is_enabled BOOLEAN NOT NULL DEFAULT false,
  config JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(user_id, flag_name)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_feature_flags_user_name ON feature_flags(user_id, flag_name);

-- Enable Row Level Security
ALTER TABLE feature_flags ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view own feature flags" ON feature_flags;
DROP POLICY IF EXISTS "Users can insert own feature flags" ON feature_flags;
DROP POLICY IF EXISTS "Users can update own feature flags" ON feature_flags;

-- Policies
CREATE POLICY "Users can view own feature flags"
  ON feature_flags FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own feature flags"
  ON feature_flags FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own feature flags"
  ON feature_flags FOR UPDATE
  USING (auth.uid() = user_id);

-- Trigger for updated_at
DROP TRIGGER IF EXISTS update_feature_flags_updated_at ON feature_flags;
CREATE TRIGGER update_feature_flags_updated_at
    BEFORE UPDATE ON feature_flags
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default flags for fact-based detection rollout
INSERT INTO feature_flags (user_id, flag_name, is_enabled, config) 
SELECT 
  id as user_id,
  'fact_based_detection' as flag_name,
  false as is_enabled,
  '{"parallel_mode": true, "compare_output": true}'::jsonb as config
FROM auth.users 
WHERE NOT EXISTS (
  SELECT 1 FROM feature_flags ff 
  WHERE ff.user_id = auth.users.id AND ff.flag_name = 'fact_based_detection'
);
