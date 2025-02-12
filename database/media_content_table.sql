-- Enable the pgvector extension
create extension if not exists vector;

-- Create the media content table
create table media_content (
    id bigserial primary key,
    media_url text not null,                                    -- URL of media content
    media_type text not null,                                   -- Type (video/podcast/audio)
    platform text not null,                                     -- Platform (YouTube/Spotify etc)
    author_id text not null,                                    -- Creator's platform ID
    author_handle text not null,                                -- Creator's username/handle
    title text not null,                                        -- Media title
    description text,                                           -- Original description
    transcript text not null,                                   -- Generated transcript
    summary text not null,                                      -- Generated summary
    metadata jsonb not null default '{}'::jsonb,               -- Additional metadata
                                                               -- ↳ duration: int (seconds)
                                                               -- ↳ views: int
                                                               -- ↳ likes: int
                                                               -- ↳ tags: string[]
    embedding vector(1536) not null,                           -- Content embedding
    embedding_model varchar not null,                          -- Model used for embedding
    chunk_number integer not null,                             -- For chunked content
    publish_date timestamp with time zone,                     -- Original publish date
    document_creation_date timestamp with time zone,           -- When content was created
    document_crawl_date timestamp with time zone default timezone('utc'::text, now()) not null,  -- Last crawl date
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,  -- Record creation time

    -- Add a unique constraint
    unique(media_url, chunk_number)
);

-- Create an index for better vector similarity search performance
create index on media_content using ivfflat (embedding vector_cosine_ops);

-- Create an index on metadata for faster filtering
create index idx_media_content_metadata on media_content using gin (metadata);

-- Create indexes for common queries
create index idx_media_content_url on media_content(media_url);
create index idx_media_content_type on media_content(media_type);
create index idx_media_content_platform on media_content(platform);
create index idx_media_content_author on media_content(author_id);
create index idx_media_content_publish_date on media_content(publish_date);
create index idx_media_content_created on media_content(created_at);
create index idx_media_content_crawl_date on media_content(document_crawl_date);

-- Create a function to search for media content
create function match_media_content (
  query_embedding vector(1536),
  match_count int default 10,
  filter jsonb DEFAULT '{}'::jsonb
) returns table (
    id bigint,
    media_url text,
    media_type text,
    platform text,
    author_id text,
    author_handle text,
    title text,
    description text,
    transcript text,
    summary text,
    metadata jsonb,
    chunk_number integer,
    publish_date timestamp with time zone,
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
    media_url,
    media_type,
    platform,
    author_id,
    author_handle,
    title,
    description,
    transcript,
    summary,
    metadata,
    chunk_number,
    publish_date,
    document_creation_date,
    document_crawl_date,
    created_at,
    1 - (media_content.embedding <=> query_embedding) as similarity
  from media_content
  where metadata @> filter
  order by media_content.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- Enable RLS
alter table media_content enable row level security;

-- Create a policy that allows anyone to read
create policy "Allow public read access"
  on media_content
  for select
  to public
  using (true);

-- Create a policy that allows authenticated users to insert/update
create policy "Allow authenticated insert"
  on media_content
  for insert
  to authenticated
  with check (true);

create policy "Allow authenticated update"
  on media_content
  for update
  to authenticated
  using (true); 