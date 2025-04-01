CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_graph_checkpoints_updated_at
    BEFORE UPDATE ON graph_checkpoints
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_shared_resources_updated_at
    BEFORE UPDATE ON shared_resources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_graph_metadata_updated_at
    BEFORE UPDATE ON graph_metadata
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column(); 