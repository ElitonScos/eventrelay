CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS events (
    id           BIGSERIAL PRIMARY KEY,
    event_id     UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    event_type   VARCHAR(100) NOT NULL,
    payload      JSONB NOT NULL DEFAULT '{}',
    status       VARCHAR(50) NOT NULL DEFAULT 'queued',
    error_msg    TEXT,
    retry_count  INT NOT NULL DEFAULT 0,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_events_status      ON events (status);
CREATE INDEX IF NOT EXISTS idx_events_event_type  ON events (event_type);
CREATE INDEX IF NOT EXISTS idx_events_created_at  ON events (created_at DESC);
