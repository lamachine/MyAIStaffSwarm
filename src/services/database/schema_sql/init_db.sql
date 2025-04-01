-- Run these in Supabase SQL editor to create tables if they don't exist

-- Check if tables exist
SELECT EXISTS (
   SELECT FROM information_schema.tables 
   WHERE table_name = 'graph_checkpoints'
);

SELECT EXISTS (
   SELECT FROM information_schema.tables 
   WHERE table_name = 'graph_metadata'
);

SELECT EXISTS (
   SELECT FROM information_schema.tables 
   WHERE table_name = 'shared_resources'
);

-- If they don't exist, create them using the SQL from:
-- src/database/graph_checkpoints_table.sql
-- src/database/graph_metadata_table.sql
-- src/database/shared_resources_table.sql 