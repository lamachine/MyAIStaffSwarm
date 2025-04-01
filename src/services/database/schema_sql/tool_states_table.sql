CREATE TABLE tool_states (
    id BIGSERIAL PRIMARY KEY,
    tool_name VARCHAR(50) NOT NULL,
    input JSONB,
    result JSONB,
    error TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_error BOOLEAN DEFAULT false
);

-- Create indexes
CREATE INDEX idx_tool_states_name ON tool_states(tool_name);
CREATE INDEX idx_tool_states_timestamp ON tool_states(timestamp);

-- Enable RLS
ALTER TABLE tool_states ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Allow public read access" ON tool_states FOR SELECT TO public USING (true);
CREATE POLICY "Allow authenticated insert" ON tool_states FOR INSERT TO authenticated WITH CHECK (true); 