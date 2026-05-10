-- Add is_summary column to chat_history table for conversation summarization
ALTER TABLE chat_history ADD COLUMN IF NOT EXISTS is_summary BOOLEAN DEFAULT FALSE;

-- Update the role check constraint to include 'system' role for summary messages
ALTER TABLE chat_history DROP CONSTRAINT IF EXISTS chat_history_role_check;
ALTER TABLE chat_history ADD CONSTRAINT chat_history_role_check CHECK (role IN ('user', 'assistant', 'system'));

-- Create index for is_summary queries (to filter out summaries efficiently)
CREATE INDEX IF NOT EXISTS idx_chat_history_is_summary ON chat_history(is_summary);
