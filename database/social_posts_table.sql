-- Enable the pgvector extension
create extension if not exists vector;

-- Create the social posts table
create table social_posts (
    id bigserial primary key,
    post_url text not null,                                     -- URL to the post
    platform text not null,                                     -- Platform (Twitter/LinkedIn etc)
    author_id text not null,                                    -- Author's platform ID
    author_handle text not null,                                -- Author's username/handle
    content text not null,                                      -- Post content
    title text,                                                 -- Generated title (if applicable)
    summary text not null,                                      -- Generated summary
    metadata jsonb not null default '{}'::jsonb,               -- Additional metadata
                                                               -- ↳ likes: int
                                                               -- ↳ shares: int
                                                               -- ↳ replies: int
                                                               -- ↳ tags: string[]
                                                               -- ↳ mentions: string[]
    embedding vector(1536) not null,                           -- Content embedding
    embedding_model varchar not null,                          -- Model used for embedding
    post_timestamp timestamp with time zone not null,          -- Original post time
    document_creation_date timestamp with time zone,           -- When post was created
    document_crawl_date timestamp with time zone default timezone('utc'::text, now()) not null,  -- Last crawl date
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,  -- Record creation time

    -- Add a unique constraint
    unique(post_url)
);

-- Create an index for better vector similarity search performance
create index on social_posts using ivfflat (embedding vector_cosine_ops);

-- Create an index on metadata for faster filtering
create index idx_social_posts_metadata on social_posts using gin (metadata);

-- Create indexes for common queries
create index idx_social_posts_url on social_posts(post_url);
create index idx_social_posts_platform on social_posts(platform);
create index idx_social_posts_author on social_posts(author_id);
create index idx_social_posts_timestamp on social_posts(post_timestamp);
create index idx_social_posts_created on social_posts(created_at);
create index idx_social_posts_crawl_date on social_posts(document_crawl_date);

-- Create a function to search for social posts
create function match_social_posts (
  query_embedding vector(1536),
  match_count int default 10,
  filter jsonb DEFAULT '{}'::jsonb
) returns table (
    id bigint,
    post_url text,
    platform text,
    author_id text,
    author_handle text,
    content text,
    title text,
    summary text,
    metadata jsonb,
    post_timestamp timestamp with time zone,
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
    post_url,
    platform,
    author_id,
    author_handle,
    content,
    title,
    summary,
    metadata,
    post_timestamp,
    document_creation_date,
    document_crawl_date,
    created_at,
    1 - (social_posts.embedding <=> query_embedding) as similarity
  from social_posts
  where metadata @> filter
  order by social_posts.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- Enable RLS
alter table social_posts enable row level security;

-- Create a policy that allows anyone to read
create policy "Allow public read access"
  on social_posts
  for select
  to public
  using (true);

-- Create a policy that allows authenticated users to insert/update
create policy "Allow authenticated insert"
  on social_posts
  for insert
  to authenticated
  with check (true);

create policy "Allow authenticated update"
  on social_posts
  for update
  to authenticated
  using (true); 