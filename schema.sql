-- Create the incidents table
CREATE TABLE IF NOT EXISTS incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT now(),
    incident_date TIMESTAMPTZ NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    location_raw TEXT,
    source_url TEXT UNIQUE NOT NULL,
    source_name TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    is_verified BOOLEAN DEFAULT false,
    image_url TEXT
);

-- Index for faster sorting by date
CREATE INDEX IF NOT EXISTS idx_incidents_date ON incidents(incident_date DESC);

-- Index for searching title and description (Basic search)
CREATE INDEX IF NOT EXISTS idx_incidents_search ON incidents USING GIN (to_tsvector('english', title || ' ' || description));

-- Comment for clarity
COMMENT ON TABLE incidents IS 'Stores Christian persecution incidents gathered from public sources.';
