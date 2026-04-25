-- Migration: Add pinecone_index column to user_settings table
-- Run this if you already have the user_settings table without the pinecone_index column

-- Add pinecone_index column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_settings' 
        AND column_name = 'pinecone_index'
    ) THEN
        ALTER TABLE user_settings ADD COLUMN pinecone_index TEXT;
    END IF;
END $$;

-- Add permissions column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_settings' 
        AND column_name = 'permissions'
    ) THEN
        ALTER TABLE user_settings ADD COLUMN permissions JSONB DEFAULT '{}'::jsonb;
    END IF;
END $$;

-- Drop pinecone_api_key column if it exists (no longer needed)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_settings' 
        AND column_name = 'pinecone_api_key'
    ) THEN
        ALTER TABLE user_settings DROP COLUMN pinecone_api_key;
    END IF;
END $$;
