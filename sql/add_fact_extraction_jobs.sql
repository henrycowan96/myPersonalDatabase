-- Create fact_extraction_jobs table for background processing
-- Run this in Supabase SQL Editor

-- Create fact_extraction_jobs table
CREATE TABLE IF NOT EXISTS fact_extraction_jobs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    sync_job_id UUID NOT NULL REFERENCES sync_jobs(id) ON DELETE CASCADE,
    source_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, processing, completed, failed
    total_chunks INTEGER NOT NULL DEFAULT 0,
    processed_chunks INTEGER NOT NULL DEFAULT 0,
    facts_extracted INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_fact_extraction_jobs_user_id ON fact_extraction_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_fact_extraction_jobs_status ON fact_extraction_jobs(status);
CREATE INDEX IF NOT EXISTS idx_fact_extraction_jobs_sync_job_id ON fact_extraction_jobs(sync_job_id);

-- Enable Row Level Security
ALTER TABLE fact_extraction_jobs ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view own fact extraction jobs" ON fact_extraction_jobs;
DROP POLICY IF EXISTS "Users can insert own fact extraction jobs" ON fact_extraction_jobs;
DROP POLICY IF EXISTS "Users can update own fact extraction jobs" ON fact_extraction_jobs;

-- Create policies
CREATE POLICY "Users can view own fact extraction jobs"
    ON fact_extraction_jobs FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own fact extraction jobs"
    ON fact_extraction_jobs FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own fact extraction jobs"
    ON fact_extraction_jobs FOR UPDATE
    USING (auth.uid() = user_id);

-- Create trigger for updated_at timestamp (reusing existing function)
DROP TRIGGER IF EXISTS update_fact_extraction_jobs_updated_at ON fact_extraction_jobs;
CREATE TRIGGER update_fact_extraction_jobs_updated_at
    BEFORE UPDATE ON fact_extraction_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
