-- Create vessel_history table with PostGIS geometry column
CREATE TABLE IF NOT EXISTS vessel_history (
    id BIGSERIAL PRIMARY KEY,
    mmsi BIGINT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL,
    position GEOMETRY(Point, 4326) NOT NULL
);
