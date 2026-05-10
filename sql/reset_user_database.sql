-- Reset User Database Function
-- This function resets a user's database by clearing all their data
-- Run this in Supabase SQL Editor to create the function

-- Drop function if it exists
DROP FUNCTION IF EXISTS reset_user_database(UUID);

-- Create function to reset user database
CREATE OR REPLACE FUNCTION reset_user_database(target_user_id UUID)
RETURNS TEXT AS $$
DECLARE
    result TEXT;
BEGIN
    -- Delete all fact-related data for the user
    DELETE FROM fact_changes
    WHERE user_id = target_user_id;

    DELETE FROM candidate_facts
    WHERE user_id = target_user_id;

    DELETE FROM facts
    WHERE user_id = target_user_id;

    -- Delete all chat history for the user
    DELETE FROM chat_history 
    WHERE user_id = target_user_id;

    -- Delete all OAuth tokens for the user
    DELETE FROM oauth_tokens 
    WHERE user_id = target_user_id;

    -- Clear permissions, reset setup_step, clear uploaded_data_sources, and remove pinecone_index
    UPDATE user_settings
    SET
        permissions = '{}'::jsonb,
        setup_step = 1,
        uploaded_data_sources = '{}'::jsonb,
        updated_at = NOW()
    WHERE user_id = target_user_id;

    -- Return success message
    result := 'User database reset successfully for user_id: ' || target_user_id;
    RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION reset_user_database(UUID) TO authenticated;
