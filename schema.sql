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
    is_active BOOLEAN DEFAULT true
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

COMMENT ON TABLE system_events IS 'Unified bucket for analytics, job logs, and error reports.';
