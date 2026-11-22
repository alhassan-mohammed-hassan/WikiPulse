CREATE TABLE IF NOT EXISTS wiki_events (
    event_id TEXT PRIMARY KEY,
    revision_id BIGINT,
    event_type VARCHAR(50) NOT NULL,
    namespace BIGINT,
    title TEXT NOT NULL,
    comment TEXT,
    username TEXT NOT NULL,
    is_bot BOOLEAN DEFAULT FALSE,
    wiki VARCHAR(100) NOT NULL,
    server_name VARCHAR(255),
    domain VARCHAR(255),
    event_timestamp BIGINT,
    event_time TIMESTAMP NOT NULL,
    ingest_time TIMESTAMP,
    event_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_wiki_events_event_time
    ON wiki_events (event_time DESC);

CREATE INDEX IF NOT EXISTS idx_wiki_events_event_type
    ON wiki_events (event_type);

CREATE INDEX IF NOT EXISTS idx_wiki_events_wiki
    ON wiki_events (wiki);

CREATE INDEX IF NOT EXISTS idx_wiki_events_event_date
    ON wiki_events (event_date);
