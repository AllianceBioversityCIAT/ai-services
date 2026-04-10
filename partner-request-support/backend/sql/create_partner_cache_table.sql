-- Table for caching processed partner request results
-- This prevents re-processing the same partner requests multiple times

CREATE TABLE IF NOT EXISTS partner_request_cache_prod (
    request_id BIGINT PRIMARY KEY,
    partner_name TEXT NOT NULL,
    acronym TEXT,
    website TEXT,
    country TEXT,
    match_found BOOLEAN DEFAULT FALSE,
    match_quality TEXT, -- 'excellent', 'good', 'fair', 'no_match', 'error'
    clarisa_match JSONB, -- Complete match data with scores
    top_candidates JSONB, -- Array of top 5 candidates with all their info
    web_search JSONB, -- Web search results if performed
    api_data JSONB, -- Original API data (request_source, external_user, created_at)
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_partner_cache_request_id ON partner_request_cache_prod(request_id);
CREATE INDEX IF NOT EXISTS idx_partner_cache_processed_at ON partner_request_cache_prod(processed_at);
CREATE INDEX IF NOT EXISTS idx_partner_cache_match_quality ON partner_request_cache_prod(match_quality);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_partner_cache_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_partner_cache_updated_at
    BEFORE UPDATE ON partner_request_cache_prod
    FOR EACH ROW
    EXECUTE FUNCTION update_partner_cache_updated_at();

-- Add comments for documentation
COMMENT ON TABLE partner_request_cache_prod IS 'Cache table for processed partner requests to avoid re-processing';
COMMENT ON COLUMN partner_request_cache_prod.request_id IS 'Partner request ID from CLARISA API';
COMMENT ON COLUMN partner_request_cache_prod.clarisa_match IS 'Best match from CLARISA with all scores';
COMMENT ON COLUMN partner_request_cache_prod.top_candidates IS 'Top 5 candidate matches with scores';
COMMENT ON COLUMN partner_request_cache_prod.web_search IS 'Web search results if performed';
COMMENT ON COLUMN partner_request_cache_prod.api_data IS 'Original API data for reference';