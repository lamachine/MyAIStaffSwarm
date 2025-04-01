-- Enable the pgvector extension
create extension if not exists vector;

-- Create the swarm messages table
create table swarm_messages (
    id bigserial primary key,
    session_id varchar not null,
    timestamp timestamp with time zone default timezone('utc'::text, now()) not null,
    sender varchar not null,  -- 'human', 'ai', 'system', etc
    target varchar not null,  -- 'orchestrator', 'user', 'system', etc
    content text not null,
    embedding vector(768) not null,
    embedding_model varchar not null default 'nomic-embed-text',
    metadata jsonb not null default '{}'::jsonb,  -- Additional context/state info
    
    -- Add a unique constraint for session ordering
    unique(session_id, timestamp)
);

-- Create indexes
create index idx_swarm_messages_session on swarm_messages(session_id);
create index idx_swarm_messages_timestamp on swarm_messages(timestamp);
create index idx_swarm_messages_sender on swarm_messages(sender);
create index idx_swarm_messages_target on swarm_messages(target);
create index idx_swarm_messages_metadata on swarm_messages using gin (metadata);

-- Vector search index
create index idx_swarm_messages_embedding on swarm_messages 
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);

-- Function to match messages using vector similarity
CREATE OR REPLACE FUNCTION match_swarm_messages (
  query_embedding vector(768),
  match_count int DEFAULT 5,
  similarity_threshold float DEFAULT 0.7,
  filter jsonb DEFAULT '{}'::jsonb
) 
RETURNS TABLE (
  id bigint,
  session_id text,
  sender text, 
  target text,
  content text,
  metadata jsonb,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    id,
    session_id,
    sender,
    target, 
    content,
    metadata,
    1 - (embedding <=> query_embedding) as similarity
  FROM swarm_messages
  WHERE 1 - (embedding <=> query_embedding) > similarity_threshold
    AND metadata @> filter
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Enable RLS
alter table swarm_messages enable row level security;

-- Create policies
create policy "Allow public read access"
  on swarm_messages
  for select
  to public
  using (true);

create policy "Allow authenticated insert"
  on swarm_messages
  for insert
  to authenticated
  with check (true);

create policy "Allow authenticated update"
  on swarm_messages
  for update
  to authenticated
  using (true); 