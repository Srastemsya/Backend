"""Durable state owned by the swipes service."""


def migrate(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS swipe_feeds (
            id text PRIMARY KEY, user_id text NOT NULL, filters jsonb NOT NULL,
            items jsonb NOT NULL, expires_at timestamptz NOT NULL
        );
        CREATE TABLE IF NOT EXISTS swipe_cursors (
            token text PRIMARY KEY, feed_id text NOT NULL REFERENCES swipe_feeds(id) ON DELETE CASCADE,
            position integer NOT NULL, UNIQUE (feed_id, position)
        );
        CREATE INDEX IF NOT EXISTS swipe_feeds_expiry ON swipe_feeds (expires_at);
        CREATE TABLE IF NOT EXISTS swipe_rooms (
            id text PRIMARY KEY, version bigint NOT NULL DEFAULT 0,
            snapshot jsonb NOT NULL, expires_at timestamptz
        );
        CREATE TABLE IF NOT EXISTS swipe_invites (
            digest text PRIMARY KEY, room_id text NOT NULL REFERENCES swipe_rooms(id),
            expires_at timestamptz NOT NULL
        );
        CREATE TABLE IF NOT EXISTS swipe_retries (
            user_id text NOT NULL, operation text NOT NULL, key text NOT NULL,
            fingerprint text NOT NULL, response jsonb NOT NULL,
            PRIMARY KEY (user_id, operation, key)
        );
        INSERT INTO schema_versions VALUES (2) ON CONFLICT DO NOTHING;
    """)
