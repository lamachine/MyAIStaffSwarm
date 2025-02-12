-- Enable the pgvector extension
create extension if not exists vector;

-- Create the social articles table
create table social_articles (
    id bigserial primary key,
    article_url text not null,                                  -- URL to the article
    platform text not null,                                     -- Platform (Medium/LinkedIn etc)
    author_id text not null,                                    -- Author's platform ID
    author_handle text not null,                                -- Author's username/handle
    title text not null,                                        -- Article title
    content text not null,                                      -- Article content
    summary text not null,                                      -- Generated summary
    metadata jsonb not null default '{}'::jsonb,               -- Additional metadata
                                                               -- ↳ likes: int
                                                               -- ↳ shares: int
                                                               -- ↳ comments: int
                                                               -- ↳ tags: string[]
                                                               -- ↳ series: string
                                                               -- ↳ reading_time: int (minutes)
    embedding vector(1536) not null,                           -- Content embedding
    embedding_model varchar not null,                          -- Model used for embedding
    chunk_number integer not null,                             -- For chunked content
    publish_timestamp timestamp with time zone not null,        -- Original publish time
    document_creation_date timestamp with time zone,           -- When article was created
    document_crawl_date timestamp with time zone default timezone('utc'::text, now()) not null,  -- Last crawl date
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,  -- Record creation time

    -- Add a unique constraint
    unique(article_url, chunk_number)
);

-- Create an index for better vector similarity search performance
create index on social_articles using ivfflat (embedding vector_cosine_ops);

-- Create an index on metadata for faster filtering
create index idx_social_articles_metadata on social_articles using gin (metadata);

-- Create indexes for common queries
create index idx_social_articles_url on social_articles(article_url);
create index idx_social_articles_platform on social_articles(platform);
create index idx_social_articles_author on social_articles(author_id);
create index idx_social_articles_timestamp on social_articles(publish_timestamp);
create index idx_social_articles_created on social_articles(created_at);
create index idx_social_articles_crawl_date on social_articles(document_crawl_date);

-- Create a function to search for social articles
create function match_social_articles (
  query_embedding vector(1536),
  match_count int default 10,
  filter jsonb DEFAULT '{}'::jsonb
) returns table (
    id bigint,
    article_url text,
    platform text,
    author_id text,
    author_handle text,
    title text,
    content text,
    summary text,
    metadata jsonb,
    chunk_number integer,
    publish_timestamp timestamp with time zone,
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
    article_url,
    platform,
    author_id,
    author_handle,
    title,
    content,
    summary,
    metadata,
    chunk_number,
    publish_timestamp,
    document_creation_date,
    document_crawl_date,
    created_at,
    1 - (social_articles.embedding <=> query_embedding) as similarity
  from social_articles
  where metadata @> filter
  order by social_articles.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- Enable RLS
alter table social_articles enable row level security;

-- Create a policy that allows anyone to read
create policy "Allow public read access"
  on social_articles
  for select
  to public
  using (true);

-- Create a policy that allows authenticated users to insert/update
create policy "Allow authenticated insert"
  on social_articles
  for insert
  to authenticated
  with check (true);

create policy "Allow authenticated update"
  on social_articles
  for update
  to authenticated
  using (true); 