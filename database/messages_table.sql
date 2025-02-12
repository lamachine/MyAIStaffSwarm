-- Enable the pgvector extension
create extension if not exists vector;

-- Create the messages table
create table messages (
    id bigserial primary key,
    user_id varchar not null,  -- Added user_id column
    role varchar not null,  -- 'user', 'assistant', 'system', etc.
    content text not null,
    embedding vector(1536),
    embedding_model varchar not null,
    conversation_id varchar not null,
    parent_message_id varchar,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    
    -- Add a unique constraint
    unique(conversation_id, id)
);

-- Create an index for better vector similarity search performance
create index on messages using ivfflat (embedding vector_cosine_ops);

-- Create an index on metadata for faster filtering
create index idx_messages_metadata on messages using gin (metadata);

-- Create an index on user_id for faster user-specific queries
create index idx_messages_user_id on messages(user_id);

-- Create a function to search for messages
create function match_messages (
  query_embedding vector(1536),
  match_count int default 10,
  filter jsonb DEFAULT '{}'::jsonb
) returns table (
    id bigint,
    user_id varchar,  -- Added to return value
    role varchar,
    content text,
    conversation_id varchar,
    parent_message_id varchar,
    metadata jsonb,
    created_at timestamp with time zone,
    similarity float
)
language plpgsql
as $$
#variable_conflict use_column
begin
  return query
  select
    id,
    user_id,  -- Added to select
    role,
    content,
    conversation_id,
    parent_message_id,
    metadata,
    created_at,
    1 - (messages.embedding <=> query_embedding) as similarity
  from messages
  where metadata @> filter
  order by messages.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- Enable RLS
alter table messages enable row level security;

-- Create a policy that allows anyone to read
create policy "Allow public read access"
  on messages
  for select
  to public
  using (true);

-- Create a policy that allows authenticated users to insert/update
create policy "Allow authenticated insert"
  on messages
  for insert
  to authenticated
  with check (true);

create policy "Allow authenticated update"
  on messages
  for update
  to authenticated
  using (true); 