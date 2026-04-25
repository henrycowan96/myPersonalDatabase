-- Create a function to get all sessions for a user with message counts
CREATE OR REPLACE FUNCTION get_user_sessions(user_uuid UUID)
RETURNS TABLE (
  session_id TEXT,
  created_at TIMESTAMP WITH TIME ZONE,
  message_count BIGINT,
  last_message TEXT
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    ch.session_id,
    MIN(ch.created_at) as created_at,
    COUNT(*) as message_count,
    (
      SELECT ch2.content 
      FROM chat_history ch2 
      WHERE ch2.user_id = ch.user_id 
        AND ch2.session_id = ch.session_id 
        AND ch2.role = 'user'
      ORDER BY ch2.created_at DESC 
      LIMIT 1
    ) as last_message
  FROM chat_history ch
  WHERE ch.user_id = user_uuid
    AND ch.session_id IS NOT NULL
  GROUP BY ch.user_id, ch.session_id
  ORDER BY MIN(ch.created_at) DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION get_user_sessions(UUID) TO authenticated;
