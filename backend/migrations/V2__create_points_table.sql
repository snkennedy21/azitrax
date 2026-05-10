-- Create points table with PostGIS geometry column
CREATE TABLE IF NOT EXISTS points (
    id BIGSERIAL PRIMARY KEY,
    geom GEOMETRY(Point, 4326),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Add spatial index for better query performance
CREATE INDEX IF NOT EXISTS idx_points_geom ON points USING GIST (geom);
