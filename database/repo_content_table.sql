-- Enable the pgvector extension
create extension if not exists vector;

-- Create the repo content table
create table repo_content (
    id bigserial primary key,
    repo_url text not null,                                     -- Repository URL
    file_path text not null,                                    -- File path within repo
    branch text not null,                                       -- Repository branch
    content text not null,                                      -- File content
    title text not null,                                        -- Generated title
    summary text not null,                                      -- Generated summary
    metadata jsonb not null default '{}'::jsonb,               -- Repository metadata
                                                               -- ↳ commit_hash: str
                                                               -- ↳ author: str
                                                               -- ↳ date: timestamp
    embedding vector(1536) not null,                           -- Content embedding
    embedding_model varchar not null,                          -- Model used for embedding
    chunk_number integer not null,                             -- For chunked content
    document_creation_date timestamp with time zone,           -- Commit date
    document_crawl_date timestamp with time zone default timezone('utc'::text, now()) not null,  -- Last crawl date
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,  -- Record creation time
    
    -- Add a unique constraint
    unique(repo_url, file_path, branch, chunk_number)
);

-- Create an index for better vector similarity search performance
create index on repo_content using ivfflat (embedding vector_cosine_ops);

-- Create an index on metadata for faster filtering
create index idx_repo_content_metadata on repo_content using gin (metadata);

-- Create indexes for common queries
create index idx_repo_content_repo on repo_content(repo_url);
create index idx_repo_content_file_path on repo_content(file_path);
create index idx_repo_content_branch on repo_content(branch);
create index idx_repo_content_created on repo_content(created_at);
create index idx_repo_content_crawl_date on repo_content(document_crawl_date);

-- Create a function to search for repository content
create function match_repo_content (
  query_embedding vector(1536),
  match_count int default 10,
  filter jsonb DEFAULT '{}'::jsonb
) returns table (
    id bigint,
    repo_url text,
    file_path text,
    branch text,
    content text,
    title text,
    summary text,
    metadata jsonb,
    chunk_number integer,
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
    repo_url,
    file_path,
    branch,
    content,
    title,
    summary,
    metadata,
    chunk_number,
    document_creation_date,
    document_crawl_date,
    created_at,
    1 - (repo_content.embedding <=> query_embedding) as similarity
  from repo_content
  where metadata @> filter
  order by repo_content.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- End of match_repo_content function
$$;

-- Create a function to count repository content documents
CREATE OR REPLACE FUNCTION count_repo_content(filter jsonb DEFAULT '{}'::jsonb)
RETURNS integer AS $$
BEGIN
  RETURN (SELECT COUNT(*) FROM repo_content WHERE metadata @> filter);
END;
$$ LANGUAGE plpgsql STABLE;

-- Create a function to list repository content documents with pagination
CREATE OR REPLACE FUNCTION list_repo_content(filter jsonb DEFAULT '{}'::jsonb, limit_count integer DEFAULT 10, offset_count integer DEFAULT 0)
RETURNS TABLE (
  id bigint,
  repo_url text,
  file_path text,
  branch text,
  content text,
  title text,
  summary text,
  metadata jsonb,
  chunk_number integer,
  document_creation_date timestamp with time zone,
  document_crawl_date timestamp with time zone,
  created_at timestamp with time zone
) AS $$
BEGIN
  RETURN QUERY
    SELECT id, repo_url, file_path, branch, content, title, summary, metadata, chunk_number, document_creation_date, document_crawl_date, created_at
    FROM repo_content
    WHERE metadata @> filter
    ORDER BY created_at DESC
    LIMIT limit_count OFFSET offset_count;
END;
$$ LANGUAGE plpgsql STABLE;

-- Enable RLS
alter table repo_content enable row level security;

-- Create a policy that allows anyone to read
create policy "Allow public read access"
  on repo_content
  for select
  to public
  using (true);

-- Create a policy that allows authenticated users to insert/update
create policy "Allow authenticated insert"
  on repo_content
  for insert
  to authenticated
  with check (true);

create policy "Allow authenticated update"
  on repo_content
  for update
  to authenticated
  using (true); 