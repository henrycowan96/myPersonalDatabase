-- Create user_feedback table for tracking insight feedback
CREATE TABLE IF NOT EXISTS user_feedback (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    insight_id VARCHAR(255) NOT NULL,
    feedback_type VARCHAR(50) NOT NULL, -- 'helpful', 'not_helpful', 'important', 'not_important', 'actioned', 'dismissed'
    entity VARCHAR(255), -- Optional entity the feedback relates to
    weight FLOAT DEFAULT 1.0, -- Weight for adjusting future recommendations
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_feedback_type CHECK (feedback_type IN ('helpful', 'not_helpful', 'important', 'not_important', 'actioned', 'dismissed'))
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_feedback_user_id ON user_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_entity ON user_feedback(entity);

-- Add RLS policies
ALTER TABLE user_feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own feedback" ON user_feedback
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own feedback" ON user_feedback
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own feedback" ON user_feedback
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own feedback" ON user_feedback
    FOR DELETE USING (auth.uid() = user_id);
