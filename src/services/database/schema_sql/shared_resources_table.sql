-- Shared resource states
CREATE TABLE shared_resources (
    id BIGSERIAL PRIMARY KEY,
    resource_type VARCHAR(50) NOT NULL,  -- 'memory', 'rag', 'tool_registry'
    resource_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    UNIQUE(resource_type, version)
);

-- Create indexes
CREATE INDEX idx_resources_type_version ON shared_resources(resource_type, version);
CREATE INDEX idx_resources_data ON shared_resources USING GIN (resource_data jsonb_path_ops);

-- Enable RLS
ALTER TABLE shared_resources ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Allow public read access" ON shared_resources FOR SELECT TO public USING (true);
CREATE POLICY "Allow authenticated insert" ON shared_resources FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "Allow authenticated update" ON shared_resources FOR UPDATE TO authenticated USING (true);

-- Create a function to search for resources
CREATE FUNCTION match_resources (
  search_type varchar,
  search_version int default null,
  filter jsonb DEFAULT '{}'::jsonb
) returns table (
    id bigint,
    resource_type varchar(50),
    resource_data jsonb,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    version integer,
    is_active boolean
)
language plpgsql
as $$
begin
  return query
  select
    id,
    resource_type,
    resource_data,
    created_at,
    updated_at,
    version,
    is_active
  from shared_resources
  where 
    resource_type = search_type
    and (search_version is null or version = search_version)
    and resource_data @> filter
  order by version desc;
end;
$$; 