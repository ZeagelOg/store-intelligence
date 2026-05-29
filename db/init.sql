CREATE TABLE IF NOT EXISTS events (
    event_id UUID PRIMARY KEY,
    event_type VARCHAR(50),
    store_id VARCHAR(50),
    visitor_id VARCHAR(50),
    timestamp TIMESTAMPTZ,
    is_staff BOOLEAN DEFAULT false
);
