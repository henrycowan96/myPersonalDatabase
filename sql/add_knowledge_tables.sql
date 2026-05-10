-- Add user_insights table for persistent insight storage
CREATE TABLE IF NOT EXISTS user_insights (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  insight_id TEXT NOT NULL,
  category TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  significance_score FLOAT NOT NULL DEFAULT 0.0,
  sources JSONB DEFAULT '[]'::jsonb,
  detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  time_context JSONB DEFAULT '{}'::jsonb,
  entities JSONB DEFAULT '[]'::jsonb,
  actionable BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
  UNIQUE(user_id, insight_id)
);

-- Add llm_thoughts table for persistent AI thought storage
CREATE TABLE IF NOT EXISTS llm_thoughts (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  thought_id TEXT NOT NULL,
  thought_type TEXT NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  prompt_used TEXT,
  generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
  UNIQUE(user_id, thought_id)
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_user_insights_user_id ON user_insights(user_id);
CREATE INDEX IF NOT EXISTS idx_user_insights_category ON user_insights(category);
CREATE INDEX IF NOT EXISTS idx_user_insights_score ON user_insights(significance_score DESC);
CREATE INDEX IF NOT EXISTS idx_user_insights_created_at ON user_insights(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_llm_thoughts_user_id ON llm_thoughts(user_id);
CREATE INDEX IF NOT EXISTS idx_llm_thoughts_type ON llm_thoughts(thought_type);
CREATE INDEX IF NOT EXISTS idx_llm_thoughts_created_at ON llm_thoughts(created_at DESC);

-- Enable Row Level Security
ALTER TABLE user_insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_thoughts ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view own insights" ON user_insights;
DROP POLICY IF EXISTS "Users can insert own insights" ON user_insights;
DROP POLICY IF EXISTS "Users can update own insights" ON user_insights;
DROP POLICY IF EXISTS "Users can delete own insights" ON user_insights;

DROP POLICY IF EXISTS "Users can view own thoughts" ON llm_thoughts;
DROP POLICY IF EXISTS "Users can insert own thoughts" ON llm_thoughts;
DROP POLICY IF EXISTS "Users can update own thoughts" ON llm_thoughts;
DROP POLICY IF EXISTS "Users can delete own thoughts" ON llm_thoughts;

-- Policy: Users can only see their own insights
CREATE POLICY "Users can view own insights"
  ON user_insights FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own insights"
  ON user_insights FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own insights"
  ON user_insights FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own insights"
  ON user_insights FOR DELETE
  USING (auth.uid() = user_id);

-- Policy: Users can only see their own thoughts
CREATE POLICY "Users can view own thoughts"
  ON llm_thoughts FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own thoughts"
  ON llm_thoughts FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own thoughts"
  ON llm_thoughts FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own thoughts"
  ON llm_thoughts FOR DELETE
  USING (auth.uid() = user_id);

-- Create trigger for updated_at timestamp
DROP TRIGGER IF EXISTS update_user_insights_updated_at ON user_insights;
CREATE TRIGGER update_user_insights_updated_at
    BEFORE UPDATE ON user_insights
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_llm_thoughts_updated_at ON llm_thoughts;
CREATE TRIGGER update_llm_thoughts_updated_at
    BEFORE UPDATE ON llm_thoughts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
