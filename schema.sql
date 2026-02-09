-- Drop existing table to start fresh with multi-source support
DROP TABLE IF EXISTS incidents;

CREATE TABLE incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT now(),
    incident_date TIMESTAMPTZ NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    location_raw TEXT DEFAULT 'India',
    -- sources is a JSONB array of { "name": "...", "url": "..." }
    sources JSONB NOT NULL DEFAULT '[]',
    tags TEXT[] DEFAULT '{}',
    is_verified BOOLEAN DEFAULT false,
    image_url TEXT,
    summary TEXT,
    -- similarity_hash helps in finding potential duplicates quickly
    similarity_hash TEXT,
    prayer_count INTEGER DEFAULT 0
);

-- Index for faster sorting by date
CREATE INDEX idx_incidents_date ON incidents(incident_date DESC);

-- Index for searching title and description
CREATE INDEX idx_incidents_search ON incidents USING GIN (to_tsvector('english', title || ' ' || description));

-- Index for the JSONB sources (to prevent duplicate URLs across different incidents)
CREATE INDEX idx_incidents_source_urls ON incidents USING GIN (sources);

-- Table for Dynamic Crawler Sources
CREATE TABLE crawler_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT now(),
    name TEXT NOT NULL,
    url_or_handle TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL, -- 'rss', 'social', 'google_search'
    source_persona TEXT DEFAULT 'NEUTRAL', -- 'WATCHDOG', 'HOSTILE', 'NEUTRAL'
    social_platform TEXT, -- 'X', 'FACEBOOK', 'YOUTUBE', 'INSTAGRAM'
    is_active BOOLEAN DEFAULT true
);

-- Table for Social Media Burner Accounts
CREATE TABLE social_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT now(),
    platform TEXT NOT NULL, -- 'X', 'FACEBOOK', etc.
    username TEXT NOT NULL,
    cookies_json TEXT, -- Session cookies string
    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMPTZ
);

-- Table for Admin Users (Simple Auth)
CREATE TABLE dashboard_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT now(),
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

-- Seed Initial Data for Crawler Sources
INSERT INTO crawler_sources (name, url_or_handle, source_type) VALUES
('ICC', 'https://www.persecution.org/feed', 'rss'),
('Morning Star News', 'https://morningstarnews.org/tag/religious-persecution/feed/', 'rss'),
('Christian Today India', 'https://www.christiantoday.co.in/rss.xml', 'rss'),
('UCA News', 'https://www.ucanews.com/rss/news', 'rss'),
('AsiaNews', 'https://www.asianews.it/index.php?l=en&art=1&size=0', 'rss'),
('UCFHR', 'UCFHR', 'social'),
('EFI_RLC', 'EFI_RLC', 'social'),
('persecution_in', 'persecution_in', 'social'),
('Google News (Persecution)', 'https://news.google.com/rss/search?q=%22Christian+persecution%22+India&hl=en-IN&gl=IN&ceid=IN:en', 'rss'),
('Google News (Attacks)', 'https://news.google.com/rss/search?q=%22Attack+on+Christians%22+India&hl=en-IN&gl=IN&ceid=IN:en', 'rss'),
('Google News (Anti-Conversion)', 'https://news.google.com/rss/search?q=%22Anti-conversion+laws%22+India&hl=en-IN&gl=IN&ceid=IN:en', 'rss');

-- Table for Prayer Tracking (Unique by Visitor ID)
CREATE TABLE incidents_prayers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT now(),
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    visitor_id UUID NOT NULL,
    UNIQUE(incident_id, visitor_id)
);

-- Index for checking if a specific visitor has prayed for an incident
CREATE INDEX idx_prayers_visitor ON incidents_prayers(visitor_id, incident_id);

-- Trigger Function to sync prayer_count in incidents table
CREATE OR REPLACE FUNCTION sync_prayer_count()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        UPDATE incidents 
        SET prayer_count = prayer_count + 1 
        WHERE id = NEW.incident_id;
    ELSIF (TG_OP = 'DELETE') THEN
        UPDATE incidents 
        SET prayer_count = prayer_count - 1 
        WHERE id = OLD.incident_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger to increment/decrement counter automatically
CREATE TRIGGER trg_sync_prayer_count
AFTER INSERT OR DELETE ON incidents_prayers
FOR EACH ROW
EXECUTE FUNCTION sync_prayer_count();

-- Comment for clarity
COMMENT ON TABLE incidents IS 'Stores Christian persecution incidents in India, grouped by event.';
COMMENT ON TABLE incidents_prayers IS 'Tracks unique prayer commitments by visitor ID.';

-- Table for Unified Analytics & System Logs
CREATE TABLE system_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT now(),
    event_type TEXT NOT NULL, -- 'FRONTEND', 'INGESTION', 'ERROR', 'ADMIN'
    event_name TEXT NOT NULL, -- 'page_view', 'job_started', 'model_failure', etc.
    visitor_id UUID, -- Optional, for frontend tracking
    severity TEXT DEFAULT 'INFO', -- 'INFO', 'WARNING', 'ERROR'
    metadata JSONB DEFAULT '{}' -- Flexible storage for error stacks, parameters, etc.
);

CREATE INDEX idx_system_events_type ON system_events(event_type);
CREATE INDEX idx_system_events_created ON system_events(created_at DESC);

-- Secure Gateway for Logs (Guards data behind admin credentials)
CREATE OR REPLACE FUNCTION get_secure_logs(p_user TEXT, p_hash TEXT)
RETURNS SETOF system_events AS $$
BEGIN
    -- Only return data if the credentials match a dashboard user
    IF EXISTS (
        SELECT 1 FROM dashboard_users 
        WHERE username = p_user AND password_hash = p_hash
    ) THEN
        RETURN QUERY SELECT * FROM system_events ORDER BY created_at DESC LIMIT 200;
    ELSE
        RETURN;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Finalize Permissions
-- Finalize Permissions for new tables
ALTER TABLE crawler_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_accounts ENABLE ROW LEVEL SECURITY;

-- Allow public read of crawler_sources (dashboard uses it)
DROP POLICY IF EXISTS "Allow public read sources" ON crawler_sources;
CREATE POLICY "Allow public read sources" ON crawler_sources FOR SELECT USING (true);

-- No public read/write for social_accounts (sensitive cookies)
-- Managed via Secure RPCs

-- Secure RPC to fetch/update social config
CREATE OR REPLACE FUNCTION manage_social_config(
    p_user TEXT, 
    p_hash TEXT, 
    p_action TEXT, 
    p_data JSONB DEFAULT '{}'
)
RETURNS JSONB AS $$
DECLARE
    v_result JSONB;
BEGIN
    -- Verify Admin
    IF NOT EXISTS (SELECT 1 FROM dashboard_users WHERE username = p_user AND password_hash = p_hash) THEN
        RETURN jsonb_build_object('success', false, 'error', 'Unauthorized');
    END IF;

    IF p_action = 'GET_ACCOUNTS' THEN
        SELECT jsonb_agg(t) INTO v_result FROM (SELECT * FROM social_accounts) t;
        RETURN jsonb_build_object('success', true, 'data', v_result);
    
    ELSIF p_action = 'UPSERT_ACCOUNT' THEN
        INSERT INTO social_accounts (platform, username, cookies_json, is_active)
        VALUES (
            p_data->>'platform', 
            p_data->>'username', 
            p_data->>'cookies_json', 
            (p_data->>'is_active')::BOOLEAN
        )
        ON CONFLICT (username) DO UPDATE SET
            cookies_json = EXCLUDED.cookies_json,
            is_active = EXCLUDED.is_active;
        RETURN jsonb_build_object('success', true);

    ELSIF p_action = 'GET_SOURCES' THEN
        SELECT jsonb_agg(t) INTO v_result FROM (SELECT * FROM crawler_sources ORDER BY name) t;
        RETURN jsonb_build_object('success', true, 'data', v_result);

    ELSIF p_action = 'UPSERT_SOURCE' THEN
        INSERT INTO crawler_sources (name, url_or_handle, source_type, source_persona, social_platform, is_active)
        VALUES (
            p_data->>'name', 
            p_data->>'url_or_handle', 
            p_data->>'source_type', 
            p_data->>'source_persona', 
            p_data->>'social_platform',
            (p_data->>'is_active')::BOOLEAN
        )
        ON CONFLICT (url_or_handle) DO UPDATE SET
            name = EXCLUDED.name,
            source_persona = EXCLUDED.source_persona,
            social_platform = EXCLUDED.social_platform,
            is_active = EXCLUDED.is_active;
        RETURN jsonb_build_object('success', true);

    ELSE
        RETURN jsonb_build_object('success', false, 'error', 'Invalid Action');
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON TABLE system_events IS 'Unified bucket for analytics, job logs, and error reports.';
COMMENT ON TABLE social_accounts IS 'Sensitive store for social media session cookies.';
