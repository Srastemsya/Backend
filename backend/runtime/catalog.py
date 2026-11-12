from datetime import datetime, timezone
from enum import Enum
import json
import math
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field, field_validator
from psycopg.rows import dict_row

from runtime import ApiError, CACHE, authenticate, connect

router = APIRouter(prefix="/v1")
PAGE_SIZE = 20
CURSOR_TTL = 1800
CACHE_TTL = 300
VLADIVOSTOK = "Asia/Vladivostok"


class Kind(str, Enum):
    EVENT = "EVENT"
    PLACE = "PLACE"
    ACTIVITY = "ACTIVITY"


class Filters(BaseModel):
    kind: Kind | None = None
    categoryId: str | None = Field(default=None, min_length=1)
    localDate: str | None = None
    maxPriceMinor: int | None = Field(default=None, ge=0, le=9223372036854775807)
    onlyWithSeats: bool = False

    @field_validator("localDate")
    @classmethod
    def check_local_date(cls, value):
        if value is not None and datetime.strptime(value, "%Y-%m-%d").date().isoformat() != value:
            raise ValueError("Expected YYYY-MM-DD")
        return value


class SearchQuery(Filters):
    q: str | None = None
    cursor: str | None = Field(default=None, min_length=1, max_length=128)


class MapQuery(Filters):
    kind: Kind
    bbox: str
    cursor: str | None = Field(default=None, min_length=1, max_length=128)


def viewer(request: Request):
    return authenticate(request, complete=True)[0]


Viewer = Annotated[str, Depends(viewer)]


def db_connection():
    db = connect()
    db.row_factory = dict_row
    return db


def cached_metadata(db, name, query):
    # Read a revision and its data in the same repeatable-read transaction.
    revision = db.execute("SELECT revision FROM catalog_cache_revision").fetchone()["revision"]
    key = f"cache:catalog:{name}:{revision}"
    cached = CACHE.get(key)
    if cached is not None:
        return json.loads(cached)
    items = db.execute(query).fetchall()
    CACHE.set(key, json.dumps(items, ensure_ascii=False), ex=CACHE_TTL)
    return items


CATEGORIES = "SELECT id, label, kinds FROM catalog_categories ORDER BY position, id"
COLLECTIONS = "SELECT id, title, NULL AS cover, filters FROM catalog_collections ORDER BY position, id"
SELECT_OBJECTS = """
    SELECT o.*, seats.confirmed_count
    FROM catalog_objects o
    LEFT JOIN LATERAL (
        SELECT count(*) AS confirmed_count FROM catalog_registrations
        WHERE event_id = o.id AND status = 'CONFIRMED' AND o.kind = 'EVENT'
    ) seats ON o.capacity IS NOT NULL
"""


def timestamp(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if value else None


def card(row):
    kind = row["kind"]
    admission = None
    if kind == "EVENT":
        capacity = row["capacity"]
        if capacity is None:
            admission = {"type": "OPEN"}
        else:
            confirmed = row["confirmed_count"]
            admission = {"type": "REGISTRATION", "capacity": capacity,
                         "confirmedCount": confirmed, "remainingCount": capacity - confirmed}
    price = row["price_minor"]
    return {
        "ref": {"kind": kind, "id": row["id"]},
        "title": row["title"],
        "categoryId": row["category_id"],
        "cover": row["cover"],
        "location": {"latitude": row["latitude"], "longitude": row["longitude"], "address": row["address"]},
        "price": {"amountMinor": price, "currency": "RUB"} if price is not None else None,
        "startsAt": timestamp(row["starts_at"]),
        "admission": admission,
    }


def detail(kind, identifier, user_id):
    with db_connection() as db:
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        row = db.execute(SELECT_OBJECTS + " WHERE o.published AND o.kind = %s AND o.id = %s",
                         (kind.value, identifier)).fetchone()
        if row is None:
            raise ApiError(404, "NOT_FOUND")
        fields = card(row)
        if kind != Kind.EVENT:
            return {"card": fields, "description": row["description"]}
        registration = db.execute("""
            SELECT * FROM catalog_registrations WHERE event_id = %s AND user_id = %s
        """, (identifier, user_id)).fetchone()
        saved = db.execute("""
            SELECT 1 FROM catalog_saved_events WHERE event_id = %s AND user_id = %s
        """, (identifier, user_id)).fetchone() is not None
    now = datetime.now(timezone.utc)
    phase = "UPCOMING" if now < row["starts_at"] else "ONGOING" if now < row["ends_at"] else "PAST"
    if row["organizer_id"] == user_id:
        role = "ORGANIZER"
    elif registration and registration["status"] == "CONFIRMED":
        role = "ATTENDEE"
    else:
        role = "VISITOR"
    admission = fields["admission"]
    return {
        **{key: value for key, value in fields.items() if key != "ref"},
        "id": identifier,
        "organizerId": row["organizer_id"],
        "description": row["description"],
        "endsAt": timestamp(row["ends_at"]),
        "timeZone": row["time_zone"],
        "phase": phase,
        "viewer": {
            "role": role,
            "registration": {
                "id": registration["id"], "eventId": identifier, "userId": user_id,
                "status": registration["status"], "createdAt": timestamp(registration["created_at"]),
                "removedAt": timestamp(registration["removed_at"]),
            } if registration else None,
            "canRegister": role == "VISITOR" and registration is None and phase == "UPCOMING"
            and admission["type"] == "REGISTRATION" and admission["remainingCount"] > 0,
            "canReadChat": False,
            "canPostChat": False,
            "saved": saved,
        },
    }


def parse_bbox(raw):
    try:
        west, south, east, north = map(float, raw.split(","))
    except ValueError:
        raise ApiError(422, "VALIDATION_ERROR", details={"fields": {"bbox": "INVALID_BOUNDS"}}) from None
    if not (all(map(math.isfinite, (west, south, east, north))) and
            -180 <= west <= east <= 180 and -90 <= south <= north <= 90):
        raise ApiError(422, "VALIDATION_ERROR", details={"fields": {"bbox": "INVALID_BOUNDS"}})
    return west, south, east, north


def object_page(user_id, filters, cursor, *, q=None, bounds=None):
    if filters.kind in {Kind.PLACE, Kind.ACTIVITY} and (filters.localDate or filters.onlyWithSeats):
        raise ApiError(400, "BAD_REQUEST")
    conditions = ["o.published"]
    params = []
    if filters.kind is not None:
        conditions.append("o.kind = %s")
        params.append(filters.kind.value)
    if filters.categoryId is not None:
        conditions.append("o.category_id = %s")
        params.append(filters.categoryId)
    if filters.localDate is not None:
        conditions.append("(o.starts_at AT TIME ZONE %s)::date = %s::date")
        params.extend((VLADIVOSTOK, filters.localDate))
    if filters.maxPriceMinor is not None:
        conditions.append("o.price_minor <= %s")
        params.append(filters.maxPriceMinor)
    if filters.onlyWithSeats:
        conditions.append("o.capacity > seats.confirmed_count")
    if q:
        conditions.append("(strpos(lower(o.title), lower(%s)) > 0 OR strpos(lower(o.description), lower(%s)) > 0)")
        params.extend((q, q))
    if bounds:
        west, south, east, north = bounds
        conditions.append("o.longitude BETWEEN %s AND %s AND o.latitude BETWEEN %s AND %s")
        params.extend((west, east, south, north))

    scope = [user_id, filters.model_dump(mode="json"), q, list(bounds) if bounds else None]
    if cursor:
        encoded = CACHE.get(f"cache:catalog:cursor:{cursor}")
        state = json.loads(encoded) if encoded else None
        if state is None or state["scope"] != scope:
            raise ApiError(409, "CURSOR_EXPIRED")
        conditions.append("(o.kind, o.id) > (%s, %s)")
        params.extend(state["after"])
    query = SELECT_OBJECTS + " WHERE " + " AND ".join(conditions) + " ORDER BY o.kind, o.id LIMIT %s"
    with db_connection() as db:
        rows = db.execute(query, [*params, PAGE_SIZE + 1]).fetchall()
    next_cursor = None
    if len(rows) > PAGE_SIZE:
        last = rows[PAGE_SIZE - 1]
        state = {"scope": scope, "after": [last["kind"], last["id"]]}
        next_cursor = uuid4().hex
        CACHE.set(f"cache:catalog:cursor:{next_cursor}", json.dumps(state), ex=CURSOR_TTL)
    return {"items": [card(row) for row in rows[:PAGE_SIZE]], "nextCursor": next_cursor}


@router.get("/home")
def home(user_id: Viewer):
    with db_connection() as db:
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        if not cached_metadata(db, "published", "SELECT 1 AS present FROM catalog_objects WHERE published LIMIT 1"):
            return {"quickCategories": [], "collections": [], "upcoming": []}
        categories = cached_metadata(db, "categories", CATEGORIES)
        collections = cached_metadata(db, "collections", COLLECTIONS)
        rows = db.execute(SELECT_OBJECTS + """
            WHERE o.published AND o.kind = 'EVENT' AND o.starts_at > now()
            ORDER BY o.starts_at, o.id LIMIT %s
        """, (PAGE_SIZE,)).fetchall()
    return {"quickCategories": categories, "collections": collections, "upcoming": [card(row) for row in rows]}


@router.get("/catalog/categories")
def categories(user_id: Viewer):
    with db_connection() as db:
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        return {"items": cached_metadata(db, "categories", CATEGORIES)}


@router.get("/catalog/search")
def search(user_id: Viewer, query: Annotated[SearchQuery, Query()]):
    filters = Filters.model_validate(query.model_dump())
    return object_page(user_id, filters, query.cursor, q=query.q.strip() if query.q else None)


@router.get("/catalog/map")
def map_cards(user_id: Viewer, query: Annotated[MapQuery, Query()]):
    filters = Filters.model_validate(query.model_dump())
    return object_page(user_id, filters, query.cursor, bounds=parse_bbox(query.bbox))


@router.get("/catalog/{kind}/{identifier}")
def catalog_detail(kind: Kind, identifier: str, user_id: Viewer):
    return detail(kind, identifier, user_id)


@router.get("/events/{identifier}")
def event_detail(identifier: str, user_id: Viewer):
    return detail(Kind.EVENT, identifier, user_id)
