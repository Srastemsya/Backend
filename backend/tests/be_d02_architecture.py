"""Developer checks. Run inside catalog on an isolated development stack."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

from kafka import KafkaConsumer
from starlette.requests import Request

from runtime import CACHE, ENV
from catalog import Filters, Kind, db_connection, detail, home, object_page, suggestions
from catalog_events import BOOTSTRAP, TOPIC
from dev_fixtures import dev_account_id
from events import CandidateQuery, candidates, notify_change, publish_event, register


class CatalogArchitecture(unittest.TestCase):
    def setUp(self):
        self.assertEqual(ENV, "dev")
        self.organizer = dev_account_id(1)
        self.visitor = dev_account_id(2)
        self.request = Request({"type": "http", "headers": []})
        self.key = uuid4().hex
        self.raw = {
            "title": f"BE-D02 architecture {self.key}", "description": "Synthetic verification",
            "categoryId": "culture",
            "location": {"latitude": 43.116, "longitude": 131.884, "address": "Владивосток"},
            "startsAt": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
            "timeZone": "Asia/Vladivostok", "admission": {"type": "REGISTRATION", "capacity": 1},
        }

    def publish(self):
        return publish_event(self.organizer, self.request, self.key, self.raw)

    def revision(self):
        with db_connection() as db:
            return db.execute("SELECT revision FROM catalog_cache_revision").fetchone()["revision"]

    def test_publication_and_registration_rollback_with_outbox(self):
        def fail_after_outbox(*args):
            notify_change(*args)
            raise RuntimeError("Synthetic failure after outbox write")

        revision = self.revision()
        with patch("events.notify_change", side_effect=fail_after_outbox):
            with self.assertRaises(RuntimeError):
                self.publish()
        self.assertEqual(revision, self.revision())
        with db_connection() as db:
            self.assertIsNone(db.execute("SELECT id FROM catalog_objects WHERE title = %s",
                                         (self.raw["title"],)).fetchone())
            self.assertIsNone(db.execute("SELECT key FROM catalog_event_retries WHERE key = %s",
                                         (self.key,)).fetchone())
            self.assertIsNone(db.execute("SELECT revision FROM catalog_outbox WHERE revision > %s",
                                         (revision,)).fetchone())

        event = self.publish()
        revision = self.revision()
        registration_key = uuid4().hex
        with patch("events.notify_change", side_effect=fail_after_outbox):
            with self.assertRaises(RuntimeError):
                register(self.visitor, self.request, event["id"], registration_key)
        self.assertEqual(revision, self.revision())
        with db_connection() as db:
            self.assertIsNone(db.execute("SELECT id FROM catalog_registrations WHERE event_id = %s",
                                         (event["id"],)).fetchone())
            self.assertIsNone(db.execute("SELECT key FROM catalog_event_retries WHERE key = %s",
                                         (registration_key,)).fetchone())
            self.assertIsNone(db.execute("SELECT revision FROM catalog_outbox WHERE revision > %s",
                                         (revision,)).fetchone())
        self.assertEqual(register(self.visitor, self.request, event["id"], registration_key).status_code, 201)

    def test_common_projection_and_d01_fixture_regression(self):
        event = self.publish()
        filters = Filters(kind=Kind.EVENT, categoryId="culture")
        now = datetime.now(timezone.utc)
        results = [
            object_page(self.visitor, filters, None, q=event["title"]),
            object_page(self.visitor, filters, None, bounds=(131.87, 43.10, 131.91, 43.13)),
            object_page(self.visitor, filters, None, starts_after=now),
            candidates(self.visitor, self.request, CandidateQuery(kind="EVENT", categoryId="culture")),
            {"items": home(self.visitor)["upcoming"]},
        ]
        projections = [next(card for card in result["items"] if card["ref"]["id"] == event["id"])
                       for result in results]
        self.assertTrue(all(projection == projections[0] for projection in projections))
        self.assertEqual(detail(Kind.EVENT, event["id"], self.organizer, lambda: now), event)
        self.assertEqual(detail(Kind.PLACE, "dev-vlad-museum", self.visitor, lambda: now)["card"]["ref"],
                         {"kind": "PLACE", "id": "dev-vlad-museum"})
        fixture = detail(Kind.EVENT, "dev-vlad-workshop", self.visitor, lambda: now)
        self.assertEqual(fixture["viewer"]["registration"]["status"], "CONFIRMED")

    def test_search_suggestions_omit_empty_and_draft_titles(self):
        self.assertEqual(suggestions(self.visitor), {"items": []})
        self.assertEqual(suggestions(self.visitor, "  "), {"items": []})
        self.assertEqual(suggestions(self.visitor, "городской музей"),
                         {"items": [{"label": "Городской музей", "query": "Городской музей"}]})
        self.assertEqual(suggestions(self.visitor, "Черновик экскурсии"), {"items": []})

    def test_kafka_delivery_and_revision_cache_invalidation(self):
        previous = self.revision()
        key = f"cache:catalog:published:{previous}"
        home(self.visitor)
        self.assertIsNotNone(CACHE.get(key))
        event = self.publish()
        revision = self.revision()
        deadline = time.monotonic() + 25
        consumer = KafkaConsumer(TOPIC, bootstrap_servers=BOOTSTRAP, auto_offset_reset="earliest",
                                 group_id=f"catalog-check-{self.key}", enable_auto_commit=False)
        with closing(consumer):
            change = None
            while time.monotonic() < deadline and change is None:
                for records in consumer.poll(timeout_ms=500).values():
                    for record in records:
                        payload = json.loads(record.value)
                        if payload["objectId"] == event["id"]:
                            self.assertEqual(record.key.decode(), event["id"])
                            change = payload
            self.assertIsNotNone(change, "No Kafka record for the committed publication")
        self.assertEqual(set(change), {"eventId", "type", "kind", "objectId", "revision", "occurredAt"})
        self.assertEqual(change["type"], "CATALOG_OBJECT_CHANGED")
        self.assertEqual(change["kind"], "EVENT")
        self.assertEqual(change["revision"], revision)
        while CACHE.get(key) is not None and time.monotonic() < deadline:
            time.sleep(0.2)
        self.assertIsNone(CACHE.get(key), "Kafka consumer did not invalidate the previous revision")
        with db_connection() as db:
            outbox = db.execute("SELECT * FROM catalog_outbox WHERE revision = %s", (revision,)).fetchone()
        self.assertEqual(outbox["event_id"], change["eventId"])
        self.assertIsNotNone(outbox["delivered_at"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
