-- Graph metadata and configuration
CREATE TABLE graph_metadata (
    graph_id VARCHAR(50) PRIMARY KEY,
    graph_type VARCHAR(20) NOT NULL,  -- 'main', 'research', 'personal_assistant'
    config JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_checkpoint_id BIGINT REFERENCES graph_checkpoints(id),
    is_active BOOLEAN DEFAULT true
);

-- Create indexes
CREATE INDEX idx_metadata_type ON graph_metadata(graph_type);
CREATE INDEX idx_metadata_config ON graph_metadata USING GIN (config jsonb_path_ops);

-- Enable RLS
ALTER TABLE graph_metadata ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Allow public read access" ON graph_metadata FOR SELECT TO public USING (true);
CREATE POLICY "Allow authenticated insert" ON graph_metadata FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "Allow authenticated update" ON graph_metadata FOR UPDATE TO authenticated USING (true);

-- Create a function to search graph metadata
CREATE FUNCTION match_graph_metadata (
  filter jsonb DEFAULT '{}'::jsonb
) returns table (
    graph_id varchar(50),
    graph_type varchar(20),
    config jsonb,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    last_checkpoint_id bigint,
    is_active boolean
)
language plpgsql
as $$
begin
  return query
  select
    graph_id,
    graph_type,
    config,
    created_at,
    updated_at,
    last_checkpoint_id,
    is_active
  from graph_metadata
  where config @> filter
  order by created_at desc;
end;
$$; 