"""At-least-once Kafka relay for catalog changes and metadata invalidation."""

from contextlib import contextmanager
import json
import logging
import os
from threading import Event, Thread

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
from psycopg import Error as DatabaseError
from redis import RedisError

from catalog import db_connection, timestamp
from runtime import CACHE

TOPIC = "catalog.changed.v1"
BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
BATCH_SIZE = 20


def relay_batch(producer):
    with db_connection() as db:
        rows = db.execute("""
            SELECT * FROM catalog_outbox WHERE delivered_at IS NULL
            ORDER BY revision LIMIT %s FOR UPDATE SKIP LOCKED
        """, (BATCH_SIZE,)).fetchall()
        for row in rows:
            event = {
                "eventId": row["event_id"], "type": "CATALOG_OBJECT_CHANGED", "kind": "EVENT",
                "objectId": row["object_id"], "revision": row["revision"],
                "occurredAt": timestamp(row["occurred_at"]),
            }
            producer.send(TOPIC, key=event["objectId"].encode(), value=json.dumps(event).encode()).get(timeout=4)
            db.execute("UPDATE catalog_outbox SET delivered_at = now() WHERE revision = %s",
                       (row["revision"],))


def consume_batch(consumer):
    records = consumer.poll(timeout_ms=300, max_records=BATCH_SIZE)
    for partition in records.values():
        for record in partition:
            event = json.loads(record.value)
            previous = int(event["revision"]) - 1
            CACHE.delete(*(f"cache:catalog:{name}:{previous}" for name in ("categories", "collections", "published")))
    if records:
        consumer.commit()


def kafka_worker(stop):
    logging.getLogger("kafka").setLevel(logging.CRITICAL)
    while not stop.is_set():
        producer = consumer = None
        try:
            producer = KafkaProducer(bootstrap_servers=BOOTSTRAP, acks="all", request_timeout_ms=3000,
                                     max_block_ms=3000)
            consumer = KafkaConsumer(TOPIC, bootstrap_servers=BOOTSTRAP, group_id="catalog-cache-v1",
                                     auto_offset_reset="earliest", enable_auto_commit=False)
            logging.warning("catalog kafka=ready")
            while not stop.is_set():
                relay_batch(producer)
                consume_batch(consumer)
        except (KafkaError, DatabaseError, RedisError, ValueError, KeyError):
            if not stop.is_set():
                logging.warning("catalog event relay unavailable; retrying")
        finally:
            if consumer:
                consumer.close(autocommit=False)
            if producer:
                producer.close(timeout=0)
        stop.wait(2)


@contextmanager
def relay():
    stop = Event()
    thread = Thread(target=kafka_worker, args=(stop,), name="catalog-events", daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=5)
