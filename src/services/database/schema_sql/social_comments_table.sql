-- Enable the pgvector extension
create extension if not exists vector;

-- Create the social comments table
create table social_comments (
    id bigserial primary key,
    comment_url text not null,                                  -- URL to the comment
    parent_url text not null,                                   -- URL of parent post/comment
    platform text not null,                                     -- Platform (Twitter/LinkedIn etc)
    author_id text not null,                                    -- Author's platform ID
    author_handle text not null,                                -- Author's username/handle
    content text not null,                                      -- Comment content
    summary text not null,                                      -- Generated summary
    metadata jsonb not null default '{}'::jsonb,               -- Additional metadata
                                                               -- ↳ likes: int
                                                               -- ↳ replies: int
                                                               -- ↳ mentions: string[]
    embedding vector(1536) not null,                           -- Content embedding
    embedding_model varchar not null,                          -- Model used for embedding
    comment_timestamp timestamp with time zone not null,        -- Original comment time
    document_creation_date timestamp with time zone,           -- When comment was created
    document_crawl_date timestamp with time zone default timezone('utc'::text, now()) not null,  -- Last crawl date
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,  -- Record creation time

    -- Add a unique constraint
    unique(comment_url)
);

-- Create an index for better vector similarity search performance
create index on social_comments using ivfflat (embedding vector_cosine_ops);

-- Create an index on metadata for faster filtering
create index idx_social_comments_metadata on social_comments using gin (metadata);

-- Create indexes for common queries
create index idx_social_comments_url on social_comments(comment_url);
create index idx_social_comments_parent on social_comments(parent_url);
create index idx_social_comments_platform on social_comments(platform);
create index idx_social_comments_author on social_comments(author_id);
create index idx_social_comments_timestamp on social_comments(comment_timestamp);
create index idx_social_comments_created on social_comments(created_at);
create index idx_social_comments_crawl_date on social_comments(document_crawl_date);

-- Create a function to search for social comments
create function match_social_comments (
  query_embedding vector(1536),
  match_count int default 10,
  filter jsonb DEFAULT '{}'::jsonb
) returns table (
    id bigint,
    comment_url text,
    parent_url text,
    platform text,
    author_id text,
    author_handle text,
    content text,
    summary text,
    metadata jsonb,
    comment_timestamp timestamp with time zone,
    document_creation_date timestamp with time zone,
    document_crawl_date timestamp with time zone,
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
    comment_url,
    parent_url,
    platform,
    author_id,
    author_handle,
    content,
    summary,
    metadata,
    comment_timestamp,
    document_creation_date,
    document_crawl_date,
    created_at,
    1 - (social_comments.embedding <=> query_embedding) as similarity
  from social_comments
  where metadata @> filter
  order by social_comments.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- Enable RLS
alter table social_comments enable row level security;

-- Create a policy that allows anyone to read
create policy "Allow public read access"
  on social_comments
  for select
  to public
  using (true);

-- Create a policy that allows authenticated users to insert/update
create policy "Allow authenticated insert"
  on social_comments
  for insert
  to authenticated
  with check (true);

create policy "Allow authenticated update"
  on social_comments
  for update
  to authenticated
  using (true); 