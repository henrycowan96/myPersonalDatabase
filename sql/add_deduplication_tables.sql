-- Add deduplication and soft-delete tracking tables
-- This migration adds infrastructure for robust duplicate detection and stale data handling

-- 1. Create sync_jobs table FIRST (since other tables reference it)
CREATE TABLE IF NOT EXISTS sync_jobs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    items_processed INTEGER DEFAULT 0,
    items_created INTEGER DEFAULT 0,
    items_updated INTEGER DEFAULT 0,
    items_skipped INTEGER DEFAULT 0,
    items_deleted INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Track all source IDs seen in this sync for stale detection
    source_ids_seen TEXT[]
);

-- Indexes for sync jobs
CREATE INDEX IF NOT EXISTS idx_sync_jobs_user_id ON sync_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_sync_jobs_source_type ON sync_jobs(source_type);
CREATE INDEX IF NOT EXISTS idx_sync_jobs_status ON sync_jobs(status);
CREATE INDEX IF NOT EXISTS idx_sync_jobs_started_at ON sync_jobs(started_at);

-- Enable Row Level Security
ALTER TABLE sync_jobs ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view own sync jobs" ON sync_jobs;
DROP POLICY IF EXISTS "Users can insert own sync jobs" ON sync_jobs;
DROP POLICY IF EXISTS "Users can update own sync jobs" ON sync_jobs;

-- Policy: Users can view their own sync jobs
CREATE POLICY "Users can view own sync jobs"
  ON sync_jobs FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own sync jobs"
  ON sync_jobs FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own sync jobs"
  ON sync_jobs FOR UPDATE
  USING (auth.uid() = user_id);

-- Create trigger for updated_at timestamp
DROP TRIGGER IF EXISTS update_sync_jobs_updated_at ON sync_jobs;
CREATE TRIGGER update_sync_jobs_updated_at
    BEFORE UPDATE ON sync_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 2. Create ingested_chunks table (can now reference sync_jobs)
CREATE TABLE IF NOT EXISTS ingested_chunks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL, -- 'apple_notes', 'google_drive', 'gmail', etc.
    source_id VARCHAR(255), -- Original ID from source (e.g., note UUID, email message ID)
    chunk_hash VARCHAR(64) NOT NULL, -- SHA-256 hash of chunk content
    pinecone_vector_id VARCHAR(255), -- ID of the vector in Pinecone
    content_preview TEXT, -- First 200 chars for debugging
    metadata JSONB DEFAULT '{}'::jsonb,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMP WITH TIME ZONE,
    sync_job_id UUID REFERENCES sync_jobs(id) ON DELETE SET NULL,
    
    -- Ensure unique chunks per user per source
    UNIQUE(user_id, source_type, chunk_hash)
);

-- Indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_ingested_chunks_user_id ON ingested_chunks(user_id);
CREATE INDEX IF NOT EXISTS idx_ingested_chunks_source_type ON ingested_chunks(source_type);
CREATE INDEX IF NOT EXISTS idx_ingested_chunks_source_id ON ingested_chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_ingested_chunks_chunk_hash ON ingested_chunks(chunk_hash);
CREATE INDEX IF NOT EXISTS idx_ingested_chunks_is_deleted ON ingested_chunks(is_deleted);
CREATE INDEX IF NOT EXISTS idx_ingested_chunks_last_seen ON ingested_chunks(last_seen_at);

-- Enable Row Level Security
ALTER TABLE ingested_chunks ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view own ingested chunks" ON ingested_chunks;
DROP POLICY IF EXISTS "Users can insert own ingested chunks" ON ingested_chunks;
DROP POLICY IF EXISTS "Users can update own ingested chunks" ON ingested_chunks;
DROP POLICY IF EXISTS "Users can delete own ingested chunks" ON ingested_chunks;

-- Policy: Users can view their own ingested chunks
CREATE POLICY "Users can view own ingested chunks"
  ON ingested_chunks FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own ingested chunks"
  ON ingested_chunks FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own ingested chunks"
  ON ingested_chunks FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own ingested chunks"
  ON ingested_chunks FOR DELETE
  USING (auth.uid() = user_id);

-- 3. Create data_sources table if it doesn't exist (needed by documents table)
CREATE TABLE IF NOT EXISTS data_sources (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL, -- 'google_drive', 'apple_notes', 'gmail', etc.
    source_name VARCHAR(255) NOT NULL,
    connection_config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    last_sync TIMESTAMP WITH TIME ZONE,
    sync_frequency VARCHAR(20) DEFAULT 'daily', -- 'hourly', 'daily', 'weekly'
    sync_status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'syncing', 'completed', 'failed'
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for data_sources
CREATE INDEX IF NOT EXISTS idx_data_sources_user_id ON data_sources(user_id);
CREATE INDEX IF NOT EXISTS idx_data_sources_type ON data_sources(source_type);
CREATE INDEX IF NOT EXISTS idx_data_sources_active ON data_sources(is_active);

-- Enable Row Level Security
ALTER TABLE data_sources ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view own data sources" ON data_sources;
DROP POLICY IF EXISTS "Users can insert own data sources" ON data_sources;
DROP POLICY IF EXISTS "Users can update own data sources" ON data_sources;
DROP POLICY IF EXISTS "Users can delete own data sources" ON data_sources;

-- Policy: Users can view their own data sources
CREATE POLICY "Users can view own data sources"
  ON data_sources FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own data sources"
  ON data_sources FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own data sources"
  ON data_sources FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own data sources"
  ON data_sources FOR DELETE
  USING (auth.uid() = user_id);

-- Create trigger for updated_at timestamp
DROP TRIGGER IF EXISTS update_data_sources_updated_at ON data_sources;
CREATE TRIGGER update_data_sources_updated_at
    BEFORE UPDATE ON data_sources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 4. Create documents table if it doesn't exist (based on schema)
CREATE TABLE IF NOT EXISTS documents (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    data_source_id UUID REFERENCES data_sources(id) ON DELETE SET NULL,
    title VARCHAR(500),
    content TEXT,
    content_hash VARCHAR(64) UNIQUE, -- SHA-256 hash for deduplication
    file_path TEXT,
    file_size BIGINT,
    mime_type VARCHAR(100),
    source_type VARCHAR(50), -- 'apple_notes', 'google_drive', 'gmail', etc.
    source_id VARCHAR(255), -- Original ID from source
    author VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE,
    modified_at TIMESTAMP WITH TIME ZONE,
    indexed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT false,
    quality_score DECIMAL(3,2) DEFAULT 0.0,
    metadata JSONB DEFAULT '{}'::jsonb,
    tags TEXT[],
    category VARCHAR(100),
    language VARCHAR(10) DEFAULT 'en'
);

-- Create indexes for documents table
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_data_source_id ON documents(data_source_id);
CREATE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(content_hash);
CREATE INDEX IF NOT EXISTS idx_documents_source_type ON documents(source_type);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_indexed_at ON documents(indexed_at);
CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category);
CREATE INDEX IF NOT EXISTS idx_documents_tags ON documents USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON documents USING GIN(metadata);

-- Enable Row Level Security
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view own documents" ON documents;
DROP POLICY IF EXISTS "Users can insert own documents" ON documents;
DROP POLICY IF EXISTS "Users can update own documents" ON documents;
DROP POLICY IF EXISTS "Users can delete own documents" ON documents;

-- Policy: Users can view their own documents
CREATE POLICY "Users can view own documents"
  ON documents FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own documents"
  ON documents FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own documents"
  ON documents FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own documents"
  ON documents FOR DELETE
  USING (auth.uid() = user_id);

-- 5. Add soft-delete columns to documents table (if not already present)
ALTER TABLE documents 
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS last_sync_job_id UUID REFERENCES sync_jobs(id) ON DELETE SET NULL;

-- Create index for soft-delete queries
CREATE INDEX IF NOT EXISTS idx_documents_is_deleted ON documents(is_deleted);
CREATE INDEX IF NOT EXISTS idx_documents_deleted_at ON documents(deleted_at);

-- 7. Create function to mark stale data as deleted
CREATE OR REPLACE FUNCTION mark_stale_data(user_id_param UUID, source_type_param VARCHAR, current_source_ids TEXT[], sync_job_id_param UUID)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Mark chunks not seen in current sync as deleted
    UPDATE ingested_chunks
    SET is_deleted = true,
        deleted_at = NOW(),
        sync_job_id = sync_job_id_param
    WHERE user_id = user_id_param
      AND source_type = source_type_param
      AND is_deleted = false
      AND (source_id IS NULL OR source_id = ANY(current_source_ids) IS NOT TRUE);
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Also mark corresponding documents as deleted
    UPDATE documents
    SET is_deleted = true,
        deleted_at = NOW(),
        last_sync_job_id = sync_job_id_param
    WHERE user_id = user_id_param
      AND source_type = source_type_param
      AND is_deleted = false
      AND source_id IS NOT NULL
      AND source_id = ANY(current_source_ids) IS NOT TRUE;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- 8. Create function to clean up deleted vectors from Pinecone tracking
CREATE OR REPLACE FUNCTION get_deleted_vectors_for_cleanup(user_id_param UUID, older_than_days INTEGER DEFAULT 7)
RETURNS TABLE (
    chunk_id UUID,
    pinecone_vector_id VARCHAR,
    deleted_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT ic.id, ic.pinecone_vector_id, ic.deleted_at
    FROM ingested_chunks ic
    WHERE ic.user_id = user_id_param
      AND ic.is_deleted = true
      AND ic.deleted_at < NOW() - (older_than_days || ' days')::INTERVAL
      AND ic.pinecone_vector_id IS NOT NULL
    ORDER BY ic.deleted_at ASC;
END;
$$ LANGUAGE plpgsql;

-- Grant necessary permissions (adjust based on your auth setup)
-- GRANT ALL ON ingested_chunks TO authenticated;
-- GRANT ALL ON sync_jobs TO authenticated;
-- GRANT EXECUTE ON FUNCTION mark_stale_data TO authenticated;
-- GRANT EXECUTE ON FUNCTION get_deleted_vectors_for_cleanup TO authenticated;
