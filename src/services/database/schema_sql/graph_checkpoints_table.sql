-- Enable the pgvector extension if not already enabled
create extension if not exists vector;

-- Graph checkpoints table
CREATE TABLE graph_checkpoints (
    id BIGSERIAL PRIMARY KEY,
    graph_id VARCHAR(50) NOT NULL,
    conversation_id UUID,
    state_data JSONB NOT NULL,
    summary TEXT,
    embedding VECTOR(768),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    checkpoint_type VARCHAR(20) DEFAULT 'auto',
    is_stable BOOLEAN DEFAULT true,
    UNIQUE(graph_id, conversation_id)
);

-- Create indexes
CREATE INDEX idx_checkpoints_graph_id ON graph_checkpoints(graph_id);
CREATE INDEX idx_checkpoints_created_at ON graph_checkpoints(created_at);
CREATE INDEX idx_checkpoints_conversation ON graph_checkpoints(conversation_id, created_at DESC);
CREATE INDEX idx_checkpoints_state_data ON graph_checkpoints USING GIN (state_data jsonb_path_ops);
CREATE INDEX idx_checkpoints_embedding ON graph_checkpoints USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Enable RLS
ALTER TABLE graph_checkpoints ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Allow public read access" ON graph_checkpoints FOR SELECT TO public USING (true);
CREATE POLICY "Allow authenticated insert" ON graph_checkpoints FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "Allow authenticated update" ON graph_checkpoints FOR UPDATE TO authenticated USING (true);

-- Create a function to search for checkpoints
CREATE FUNCTION match_checkpoints (
  query_embedding vector(768),
  match_count int default 10,
  filter jsonb DEFAULT '{}'::jsonb
) returns table (
    id bigint,
    graph_id varchar(50),
    conversation_id uuid,
    state_data jsonb,
    summary text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    checkpoint_type varchar(20),
    is_stable boolean,
    similarity float
)
language plpgsql
as $$
#variable_conflict use_column
begin
  return query
  select
    id,
    graph_id,
    conversation_id,
    state_data,
    summary,
    created_at,
    updated_at,
    checkpoint_type,
    is_stable,
    1 - (graph_checkpoints.embedding <=> query_embedding) as similarity
  from graph_checkpoints
  where state_data @> filter
  order by graph_checkpoints.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- Add trigger for updated_at
CREATE TRIGGER update_graph_checkpoints_updated_at
    BEFORE UPDATE ON graph_checkpoints
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column(); 