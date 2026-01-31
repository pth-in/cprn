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
    -- similarity_hash helps in finding potential duplicates quickly
    similarity_hash TEXT
);

-- Index for faster sorting by date
CREATE INDEX idx_incidents_date ON incidents(incident_date DESC);

-- Index for searching title and description
CREATE INDEX idx_incidents_search ON incidents USING GIN (to_tsvector('english', title || ' ' || description));

-- Index for the JSONB sources (to prevent duplicate URLs across different incidents)
CREATE INDEX idx_incidents_source_urls ON incidents USING GIN (sources);

-- Comment for clarity
COMMENT ON TABLE incidents IS 'Stores Christian persecution incidents in India, grouped by event.';
