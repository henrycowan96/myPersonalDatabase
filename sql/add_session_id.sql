-- Add session_id column to chat_history table
ALTER TABLE chat_history ADD COLUMN IF NOT EXISTS session_id TEXT;

-- Create index for session_id queries
CREATE INDEX IF NOT EXISTS idx_chat_history_session_id ON chat_history(session_id);

-- Create composite index for user_id + session_id queries
CREATE INDEX IF NOT EXISTS idx_chat_history_user_session ON chat_history(user_id, session_id);
