-- Create new tables
--  Open supabase studio.  localhost:3001
--  Select SQL Editor from the left menu.  
--  Copy code from this script and paste into the editor window.  
--  Click Run.



-- Enable the pgvector extension
create extension if not exists vector;

-- Create the documentation chunks table
create table dev_docs_site_pages (
    id bigserial primary key,
    url varchar not null,                                        -- Documentation page URL
    chunk_number integer not null,                              -- For chunked content
    title varchar not null,                                     -- Page/section title
    summary varchar not null,                                   -- Generated summary
    content text not null,                                      -- Documentation content
    metadata jsonb not null default '{}'::jsonb,               -- Source info, tags, etc.
                                                               -- ↳ source: str
                                                               -- ↳ owner: str
                                                               -- ↳ crawled_at: timestamp
    embedding vector(1536) not null,                           -- Content embedding
    embedding_model varchar not null,                          -- Model used for embedding
    document_creation_date timestamp with time zone,           -- Original doc date
    document_crawl_date timestamp with time zone default timezone('utc'::text, now()) not null,  -- Last crawl date
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,  -- Record creation time
    
    -- Add a unique constraint to prevent duplicate chunks for the same URL
    unique(url, chunk_number)
);

-- Create an index for better vector similarity search performance
create index on dev_docs_site_pages using ivfflat (embedding vector_cosine_ops);

-- Create an index on metadata for faster filtering
create index idx_dev_docs_site_pages_metadata on dev_docs_site_pages using gin (metadata);

-- Create indexes for common queries
create index idx_dev_docs_site_pages_url on dev_docs_site_pages(url);
create index idx_dev_docs_site_pages_created on dev_docs_site_pages(created_at);
create index idx_dev_docs_site_pages_crawl_date on dev_docs_site_pages(document_crawl_date);

-- Create a function to search for documentation chunks
create function match_dev_docs_site_pages (
  query_embedding vector(1536),
  match_count int default 10,
  filter jsonb DEFAULT '{}'::jsonb
) returns table (
    id bigint,
    url varchar,
    chunk_number integer,
    title varchar,
    summary varchar,
    content text,
    metadata jsonb,
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
    url,
    chunk_number,
    title,
    summary,
    content,
    metadata,
    document_creation_date,
    document_crawl_date,
    created_at,
    1 - (dev_docs_site_pages.embedding <=> query_embedding) as similarity
  from dev_docs_site_pages
  where metadata @> filter
  order by dev_docs_site_pages.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- End of match_dev_docs_site_pages function
$$;

-- Create a function to count documentation pages
CREATE OR REPLACE FUNCTION count_dev_docs_site_pages(filter jsonb DEFAULT '{}'::jsonb)
RETURNS integer AS $$
BEGIN
  RETURN (SELECT COUNT(*) FROM dev_docs_site_pages WHERE metadata @> filter);
END;
$$ LANGUAGE plpgsql STABLE;

-- Create a function to list documentation pages with pagination
CREATE OR REPLACE FUNCTION list_dev_docs_site_pages(filter jsonb DEFAULT '{}'::jsonb, limit_count integer DEFAULT 10, offset_count integer DEFAULT 0)
RETURNS TABLE (
  id bigint,
  url varchar,
  chunk_number integer,
  title varchar,
  summary varchar,
  content text,
  metadata jsonb,
  document_creation_date timestamp with time zone,
  document_crawl_date timestamp with time zone,
  created_at timestamp with time zone
) AS $$
BEGIN
  RETURN QUERY
    SELECT id, url, chunk_number, title, summary, content, metadata, document_creation_date, document_crawl_date, created_at
    FROM dev_docs_site_pages
    WHERE metadata @> filter
    ORDER BY created_at DESC
    LIMIT limit_count OFFSET offset_count;
END;
$$ LANGUAGE plpgsql STABLE;

-- Everything above will work for any PostgreSQL database. The below commands are for Supabase security

-- Enable RLS on the table
alter table dev_docs_site_pages enable row level security;

-- Create a policy that allows anyone to read
create policy "Allow public read access"
  on dev_docs_site_pages
  for select
  to public
  using (true);

-- Create a policy that allows authenticated users to insert/update
create policy "Allow authenticated insert"
  on dev_docs_site_pages
  for insert
  to authenticated
  with check (true);

create policy "Allow authenticated update"
  on dev_docs_site_pages
  for update
  to authenticated
  using (true);