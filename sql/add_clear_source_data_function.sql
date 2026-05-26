-- Add function to clear data for a specific source type
-- Run this in Supabase SQL Editor to create the function

-- Drop function if it exists
DROP FUNCTION IF EXISTS clear_source_data(UUID, VARCHAR);

-- Create function to clear data for a specific source type
CREATE OR REPLACE FUNCTION clear_source_data(target_user_id UUID, source_type_param VARCHAR)
RETURNS TEXT AS $$
DECLARE
    result TEXT;
BEGIN
    -- Delete ingested chunks for the specific source type
    DELETE FROM ingested_chunks
    WHERE user_id = target_user_id
      AND source_type = source_type_param;

    -- Delete sync jobs for the specific source type
    DELETE FROM sync_jobs
    WHERE user_id = target_user_id
      AND source_type = source_type_param;

    -- Delete fact_changes that reference chunks from this source
    DELETE FROM fact_changes
    WHERE user_id = target_user_id
      AND old_fact_id IN (
          SELECT id FROM facts
          WHERE user_id = target_user_id
          AND id IN (
              SELECT unnest(source_chunk_ids) FROM ingested_chunks
              WHERE user_id = target_user_id
              AND source_type = source_type_param
          )
      )
      OR new_fact_id IN (
          SELECT id FROM facts
          WHERE user_id = target_user_id
          AND id IN (
              SELECT unnest(source_chunk_ids) FROM ingested_chunks
              WHERE user_id = target_user_id
              AND source_type = source_type_param
          )
      );

    -- Delete candidate_facts that reference chunks from this source
    DELETE FROM candidate_facts
    WHERE user_id = target_user_id
      AND source_chunk_ids && ARRAY(
          SELECT unnest(source_chunk_ids) FROM ingested_chunks
          WHERE user_id = target_user_id
          AND source_type = source_type_param
      );

    -- Delete facts that reference chunks from this source
    DELETE FROM facts
    WHERE user_id = target_user_id
      AND source_chunk_ids && ARRAY(
          SELECT unnest(source_chunk_ids) FROM ingested_chunks
          WHERE user_id = target_user_id
          AND source_type = source_type_param
      );

    -- Update user_settings to remove this source from uploaded_data_sources
    UPDATE user_settings
    SET
        uploaded_data_sources = uploaded_data_sources - source_type_param,
        updated_at = NOW()
    WHERE user_id = target_user_id;

    -- Return success message
    result := 'Cleared data for source_type: ' || source_type_param || ' for user_id: ' || target_user_id;
    RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION clear_source_data(UUID, VARCHAR) TO authenticated;
