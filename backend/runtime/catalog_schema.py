"""Catalog-owned schema and idempotent Vladivostok fixtures."""

from datetime import datetime, timedelta, timezone

from psycopg.types.json import Jsonb


from dev_fixtures import dev_account_id


def migrate(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS catalog_categories (
            id text PRIMARY KEY, label text NOT NULL, kinds text[] NOT NULL,
            position integer NOT NULL
        );
        CREATE TABLE IF NOT EXISTS catalog_collections (
            id text PRIMARY KEY, title text NOT NULL, filters jsonb NOT NULL,
            position integer NOT NULL
        );
        CREATE TABLE IF NOT EXISTS catalog_objects (
            kind text NOT NULL CHECK (kind IN ('EVENT', 'PLACE', 'ACTIVITY')),
            id text NOT NULL, title text NOT NULL, description text NOT NULL,
            category_id text NOT NULL REFERENCES catalog_categories(id),
            latitude double precision NOT NULL CHECK (latitude BETWEEN -90 AND 90),
            longitude double precision NOT NULL CHECK (longitude BETWEEN -180 AND 180),
            address text NOT NULL, price_minor bigint CHECK (price_minor >= 0),
            cover jsonb, published boolean NOT NULL DEFAULT false,
            organizer_id text, starts_at timestamptz, ends_at timestamptz,
            time_zone text, capacity integer CHECK (capacity > 0),
            PRIMARY KEY (kind, id),
            CHECK ((kind = 'EVENT') = (organizer_id IS NOT NULL AND
                   starts_at IS NOT NULL AND ends_at IS NOT NULL AND time_zone IS NOT NULL)),
            CHECK (ends_at > starts_at)
        );
        CREATE TABLE IF NOT EXISTS catalog_registrations (
            id text PRIMARY KEY, event_kind text NOT NULL DEFAULT 'EVENT' CHECK (event_kind = 'EVENT'),
            event_id text NOT NULL, user_id text NOT NULL,
            status text NOT NULL CHECK (status IN ('CONFIRMED', 'REMOVED')),
            created_at timestamptz NOT NULL, removed_at timestamptz,
            UNIQUE (event_id, user_id),
            FOREIGN KEY (event_kind, event_id) REFERENCES catalog_objects(kind, id)
        );
        CREATE TABLE IF NOT EXISTS catalog_saved_events (
            event_kind text NOT NULL DEFAULT 'EVENT' CHECK (event_kind = 'EVENT'),
            event_id text NOT NULL, user_id text NOT NULL, PRIMARY KEY (event_id, user_id),
            FOREIGN KEY (event_kind, event_id) REFERENCES catalog_objects(kind, id)
        );
        CREATE TABLE IF NOT EXISTS catalog_cache_revision (
            singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton), revision bigint NOT NULL
        );
        INSERT INTO catalog_cache_revision VALUES (true, 0) ON CONFLICT DO NOTHING;
        CREATE OR REPLACE FUNCTION advance_catalog_cache_revision() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            UPDATE catalog_cache_revision SET revision = revision + 1;
            RETURN NULL;
        END;
        $$;
    """)
    for table in ("catalog_categories", "catalog_collections", "catalog_objects"):
        db.execute(f"""
            CREATE OR REPLACE TRIGGER advance_cache_revision
            AFTER INSERT OR UPDATE OR DELETE OR TRUNCATE ON {table}
            FOR EACH STATEMENT EXECUTE FUNCTION advance_catalog_cache_revision()
        """)
    db.execute("INSERT INTO schema_versions VALUES (2) ON CONFLICT DO NOTHING")
    db.execute("""
        CREATE TABLE IF NOT EXISTS catalog_media (
            id text PRIMARY KEY, owner_id text NOT NULL, purpose text NOT NULL,
            status text NOT NULL, url text NOT NULL, expires_at timestamptz
        );
        CREATE TABLE IF NOT EXISTS catalog_event_retries (
            user_id text NOT NULL, operation text NOT NULL, key text NOT NULL,
            fingerprint text NOT NULL, status integer NOT NULL, response jsonb NOT NULL,
            PRIMARY KEY (user_id, operation, key)
        );
        CREATE TABLE IF NOT EXISTS catalog_outbox (
            revision bigint PRIMARY KEY, event_id text NOT NULL UNIQUE, object_id text NOT NULL,
            occurred_at timestamptz NOT NULL, delivered_at timestamptz
        );
        CREATE INDEX IF NOT EXISTS catalog_outbox_pending ON catalog_outbox (revision)
            WHERE delivered_at IS NULL;
        CREATE INDEX IF NOT EXISTS catalog_afisha ON catalog_objects (starts_at, id)
            WHERE published AND kind = 'EVENT';
        CREATE INDEX IF NOT EXISTS catalog_active_registrations
            ON catalog_registrations (event_id, created_at, id) WHERE status = 'CONFIRMED';
        CREATE OR REPLACE TRIGGER advance_cache_revision
        AFTER INSERT OR UPDATE OR DELETE OR TRUNCATE ON catalog_registrations
        FOR EACH STATEMENT EXECUTE FUNCTION advance_catalog_cache_revision();
    """)
    db.execute("INSERT INTO schema_versions VALUES (3) ON CONFLICT DO NOTHING")


def seed(db):
    for row in [
        ("culture", "Культура", ["EVENT", "PLACE"], 1),
        ("outdoors", "На свежем воздухе", ["EVENT", "PLACE", "ACTIVITY"], 2),
        ("food", "Еда и напитки", ["PLACE"], 3),
    ]:
        db.execute("INSERT INTO catalog_categories VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING", row)
    for identifier, title, filters, position in [
        ("culture-events", "Культурные события", {"kind": "EVENT", "categoryId": "culture"}, 1),
        ("outdoor-ideas", "На свежем воздухе", {"categoryId": "outdoors"}, 2),
        ("food-places", "Где поесть", {"kind": "PLACE", "categoryId": "food"}, 3),
    ]:
        db.execute("INSERT INTO catalog_collections VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                   (identifier, title, Jsonb(filters), position))

    now = datetime.now(timezone.utc)
    objects = [
        ("PLACE", "dev-vlad-museum", "Городской музей", "culture", 43.116, 131.884, None, True, None, None),
        ("PLACE", "dev-vlad-cafe", "Кафе у моря", "food", 43.119, 131.876, 75000, True, None, None),
        ("ACTIVITY", "dev-vlad-walk", "Прогулка по набережной", "outdoors", 43.121, 131.875, 0, True, None, None),
        ("EVENT", "dev-vlad-exhibit", "Выставка о Владивостоке", "culture", 43.116, 131.884, 0, True, 2, None),
        ("EVENT", "dev-vlad-workshop", "Мастер-класс в городе", "culture", 43.113, 131.892, 0, True, 3, 8),
        ("EVENT", "dev-vlad-draft", "Черновик экскурсии", "outdoors", 43.123, 131.876, 0, False, 4, None),
    ]
    for index in range(1, 22):
        objects.append(("EVENT", f"dev-vlad-outdoor-{index:02}", f"Прогулка по городу {index}",
                        "outdoors", 43.12, 131.9, None, True, index + 4, None))
    for kind, identifier, title, category, lat, lon, price, published, days, capacity in objects:
        starts = now + timedelta(days=days) if days else None
        db.execute("""
            INSERT INTO catalog_objects (
                kind, id, title, description, category_id, latitude, longitude,
                address, price_minor, published, organizer_id, starts_at, ends_at, time_zone, capacity
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT DO NOTHING
        """, (kind, identifier, title, f"{title}. Стендовый объект каталога.", category, lat, lon,
              "Владивосток", price, published, dev_account_id(1) if starts else None,
              starts, starts + timedelta(hours=2) if starts else None,
              "Asia/Vladivostok" if starts else None, capacity))
    db.execute("""
        INSERT INTO catalog_registrations (id, event_id, user_id, status, created_at)
        VALUES ('dev-vlad-workshop-registration', 'dev-vlad-workshop', %s, 'CONFIRMED', %s)
        ON CONFLICT DO NOTHING
    """, (dev_account_id(2), now))

    for identifier, owner, purpose, status in [
        ("dev-event-cover-person1", 1, "EVENT_COVER", "READY"),
        ("dev-event-cover-person2", 2, "EVENT_COVER", "READY"),
        ("dev-event-cover-pending", 1, "EVENT_COVER", "PENDING"),
        ("dev-event-cover-wrong-purpose", 1, "CHAT_ATTACHMENT", "READY"),
    ]:
        db.execute("""
            INSERT INTO catalog_media VALUES (%s, %s, %s, %s, %s, NULL)
            ON CONFLICT DO NOTHING
        """, (identifier, dev_account_id(owner), purpose, status,
              f"https://media.example.test/{identifier}.png"))


    seed_swipes(db)


def seed_swipes(db):
    for category, label, kinds, position in [
        ("dev-swipe-places", "Места для проверки свайпов", ["PLACE"], 90),
        ("dev-swipe-events", "События для проверки свайпов", ["EVENT"], 91),
    ]:
        db.execute("INSERT INTO catalog_categories VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                   (category, label, kinds, position))
    for index in range(1, 23):
        price = 1000 if index <= 20 else (500 if index == 21 else None)
        for kind, suffix, category in [
            ("PLACE", "place", "dev-swipe-places"),
            ("EVENT", "event", "dev-swipe-events"),
        ]:
            starts = datetime(2090, 1, 2, tzinfo=timezone.utc) + timedelta(minutes=index) if kind == "EVENT" else None
            title = f"Стендовый вариант {index}"
            db.execute("""
                INSERT INTO catalog_objects (
                    kind, id, title, description, category_id, latitude, longitude, address,
                    price_minor, published, organizer_id, starts_at, ends_at, time_zone
                ) VALUES (%s,%s,%s,%s,%s,43.12,131.9,'Владивосток',%s,true,%s,%s,%s,%s)
                ON CONFLICT DO NOTHING
            """, (kind, f"dev-swipe-{suffix}-{index:02}", title, title, category, price,
                  dev_account_id(1) if starts else None, starts,
                  starts + timedelta(hours=2) if starts else None,
                  "Asia/Vladivostok" if starts else None))
