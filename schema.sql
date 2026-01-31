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
    similarity_hash TEXT
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

-- Comment for clarity
COMMENT ON TABLE incidents IS 'Stores Christian persecution incidents in India, grouped by event.';
