from datetime import timedelta
import hashlib
import json
import re
from typing import Annotated, Literal
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request as InternalRequest, urlopen
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import JSONResponse
from psycopg.types.json import Jsonb
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, field_validator

from catalog import (
    PAGE_SIZE, SELECT_OBJECTS, VLADIVOSTOK, Filters, Kind, Viewer, card, db_connection,
    event_dto, filtered_objects, object_page, page, read_cursor, registration_dto, request_clock,
    timestamp,
)
from runtime import ApiError

router = APIRouter(prefix="/v1")
internal_router = APIRouter(prefix="/internal/catalog")
MAX_MONEY = 9223372036854775807
Cursor = Annotated[str | None, Query(min_length=1, max_length=128)]
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=256)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Location(Input):
    latitude: float = Field(ge=-90, le=90, strict=True)
    longitude: float = Field(ge=-180, le=180, strict=True)
    address: str = Field(min_length=1)

    @field_validator("latitude", "longitude", mode="before")
    @classmethod
    def coordinates_are_numbers(cls, value):
        if type(value) not in (int, float):
            raise ValueError("Expected a number")
        return value


class Money(Input):
    amountMinor: int = Field(ge=0, le=MAX_MONEY, strict=True)
    currency: Literal["RUB"]


class OpenAdmission(Input):
    type: Literal["OPEN"]


class RegistrationAdmission(Input):
    type: Literal["REGISTRATION"]
    capacity: int = Field(gt=0, le=2147483647, strict=True)


class CreateEvent(Input):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    categoryId: str = Field(min_length=1)
    coverMediaId: str | None = Field(default=None, min_length=1)
    location: Location
    price: Money | None = None
    startsAt: AwareDatetime
    endsAt: AwareDatetime | None = None
    timeZone: Literal["Asia/Vladivostok"]
    admission: Annotated[OpenAdmission | RegistrationAdmission, Field(discriminator="type")]

    @field_validator("startsAt", "endsAt", mode="before")
    @classmethod
    def timestamp_is_rfc3339(cls, value):
        if not isinstance(value, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})", value
        ):
            raise ValueError("Expected an RFC 3339 timestamp")
        return value


class AgendaQuery(BaseModel):
    categoryId: str | None = Field(default=None, min_length=1)
    localDate: str | None = None
    maxPriceMinor: int | None = Field(default=None, ge=0, le=MAX_MONEY)
    onlyWithSeats: bool = False
    cursor: str | None = Field(default=None, min_length=1, max_length=128)

    _check_local_date = field_validator("localDate")(Filters.check_local_date.__func__)


class CandidateQuery(BaseModel):
    kind: Literal["EVENT", "PLACE"]
    categoryId: str | None = Field(default=None, min_length=1)
    localDate: str | None = None
    budgetTotalMinor: int | None = Field(default=None, ge=0, le=MAX_MONEY)
    partySize: int | None = Field(default=None, gt=0, le=MAX_MONEY)

    _check_local_date = field_validator("localDate")(Filters.check_local_date.__func__)


def invalid(field, code="INVALID_VALUE"):
    return ApiError(422, "VALIDATION_ERROR", details={"fields": {field: code}})


async def empty_body(request: Request, user_id: Viewer):
    if await request.body():
        raise ApiError(400, "BAD_REQUEST")


async def event_body(request: Request, user_id: Viewer):
    try:
        return await request.json()
    except (UnicodeError, ValueError):
        raise ApiError(400, "BAD_REQUEST") from None


def lookup_retry(db, user_id, operation, key, fingerprint):
    lock_key = json.dumps([user_id, operation, key])
    db.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (lock_key,))
    retry = db.execute("""
        SELECT fingerprint, status, response FROM catalog_event_retries
        WHERE user_id = %s AND operation = %s AND key = %s
    """, (user_id, operation, key)).fetchone()
    if retry and retry["fingerprint"] != fingerprint:
        raise ApiError(409, "IDEMPOTENCY_CONFLICT")
    return retry


def record_retry(db, user_id, operation, key, fingerprint, status, payload):
    db.execute("""
        INSERT INTO catalog_event_retries VALUES (%s, %s, %s, %s, %s, %s)
    """, (user_id, operation, key, fingerprint, status, Jsonb(payload)))


def notify_change(db, identifier, now):
    db.execute("""
        INSERT INTO catalog_outbox (revision, event_id, object_id, occurred_at)
        SELECT revision, %s, %s, %s FROM catalog_cache_revision
    """, (str(uuid4()), identifier, now))


def find_event(db, identifier, *, lock=False):
    # Acquire the row lock before reading occupancy in a new READ COMMITTED snapshot.
    if lock and db.execute("""
        SELECT 1 FROM catalog_objects WHERE kind = 'EVENT' AND id = %s AND published FOR UPDATE
    """, (identifier,)).fetchone() is None:
        raise ApiError(404, "NOT_FOUND")
    row = db.execute(SELECT_OBJECTS + " WHERE o.published AND o.kind = 'EVENT' AND o.id = %s",
                     (identifier,)).fetchone()
    if row is None:
        raise ApiError(404, "NOT_FOUND")
    return row


def cover_ref(db, media_id, owner, now):
    if media_id is None:
        return None
    media = db.execute("""
        SELECT id, url, expires_at FROM catalog_media
        WHERE id = %s AND owner_id = %s AND purpose = 'EVENT_COVER' AND status = 'READY'
            AND (expires_at IS NULL OR expires_at > %s)
    """, (media_id, owner, now)).fetchone()
    if media is None:
        raise invalid("coverMediaId")
    return Jsonb({"id": media["id"], "url": media["url"], "expiresAt": timestamp(media["expires_at"])})


def parse_publication(raw, now):
    try:
        body = CreateEvent.model_validate(raw)
    except ValidationError as error:
        fields = {".".join(str(part) for part in entry["loc"] if part not in ("OPEN", "REGISTRATION"))
                  or "body": "INVALID_VALUE" for entry in error.errors()}
        raise ApiError(422, "VALIDATION_ERROR", details={"fields": fields}) from None
    if body.startsAt <= now:
        raise invalid("startsAt")
    try:
        ends_at = body.endsAt if body.endsAt is not None else body.startsAt + timedelta(hours=2)
        if ends_at <= body.startsAt:
            raise invalid("endsAt")
        # Detect timestamp offsets that cannot be represented in UTC.
        timestamp(body.startsAt)
        timestamp(ends_at)
    except OverflowError:
        raise invalid("endsAt") from None
    if isinstance(body.admission, RegistrationAdmission) and body.price and body.price.amountMinor > 0:
        raise invalid("price", "PAID_REGISTRATION_UNSUPPORTED")
    return body, ends_at


@router.get("/events")
def events(user_id: Viewer, request: Request, query: Annotated[AgendaQuery, Query()]):
    filters = Filters(kind=Kind.EVENT, **query.model_dump(exclude={"cursor"}))
    return object_page(user_id, filters, query.cursor, starts_after=request_clock(request)())


@router.post("/events", status_code=201, openapi_extra={
    "requestBody": {"required": True, "content": {"application/json": {
        "schema": {"$ref": "#/components/schemas/CreateEvent"}
    }}}
})
def publish_event(user_id: Viewer, request: Request, key: IdempotencyKey,
                  raw: Annotated[object, Depends(event_body)]):
    operation = "publish"
    try:
        fingerprint = hashlib.sha256(json.dumps(raw, sort_keys=True, allow_nan=False).encode()).hexdigest()
    except ValueError:
        raise invalid("body") from None
    with db_connection() as db:
        retry = lookup_retry(db, user_id, operation, key, fingerprint)
        if retry:
            return JSONResponse(retry["response"], status_code=retry["status"])
        now = request_clock(request)()
        body, ends_at = parse_publication(raw, now)
        if db.execute("""
            SELECT 1 FROM catalog_categories WHERE id = %s AND 'EVENT' = ANY(kinds) FOR SHARE
        """, (body.categoryId,)).fetchone() is None:
            raise invalid("categoryId")
        cover = cover_ref(db, body.coverMediaId, user_id, now)
        identifier = str(uuid4())
        db.execute("""
            INSERT INTO catalog_objects (
                kind, id, title, description, category_id, latitude, longitude, address, price_minor,
                cover, published, organizer_id, starts_at, ends_at, time_zone, capacity
            ) VALUES ('EVENT', %s, %s, %s, %s, %s, %s, %s, %s, %s, true, %s, %s, %s, %s, %s)
        """, (identifier, body.title, body.description, body.categoryId, body.location.latitude,
              body.location.longitude, body.location.address, body.price.amountMinor if body.price else None,
              cover, user_id, body.startsAt, ends_at, body.timeZone, getattr(body.admission, "capacity", None)))
        payload = event_dto(find_event(db, identifier), user_id, now)
        record_retry(db, user_id, operation, key, fingerprint, 201, payload)
        notify_change(db, identifier, now)
    return payload


def registration_result(registration, event):
    return {"registration": registration_dto(registration), "admission": card(event)["admission"]}


@router.post("/events/{identifier}/registrations", status_code=201,
             responses={200: {"description": "Existing active registration"}},
             dependencies=[Depends(empty_body)])
def register(user_id: Viewer, request: Request, identifier: str, key: IdempotencyKey):
    operation = f"register:{identifier}"
    with db_connection() as db:
        retry = lookup_retry(db, user_id, operation, key, "")
        if retry:
            return JSONResponse(retry["response"], status_code=retry["status"])
        event = find_event(db, identifier, lock=True)
        if event["organizer_id"] == user_id or event["capacity"] is None:
            raise ApiError(409, "INVALID_STATE")
        now = request_clock(request)()
        if now >= event["starts_at"]:
            raise ApiError(409, "EVENT_CLOSED")
        registration = db.execute("""
            SELECT * FROM catalog_registrations WHERE event_id = %s AND user_id = %s
        """, (identifier, user_id)).fetchone()
        if registration and registration["status"] == "REMOVED":
            raise ApiError(409, "REGISTRATION_REMOVED")
        status = 200
        if registration is None:
            if event["confirmed_count"] >= event["capacity"]:
                admission = card(event)["admission"]
                raise ApiError(409, "EVENT_FULL", details={name: admission[name] for name in
                                                         ("capacity", "confirmedCount", "remainingCount")})
            registration = db.execute("""
                INSERT INTO catalog_registrations (id, event_id, user_id, status, created_at)
                VALUES (%s, %s, %s, 'CONFIRMED', %s) RETURNING *
            """, (str(uuid4()), identifier, user_id, now)).fetchone()
            event = find_event(db, identifier)
            notify_change(db, identifier, now)
            status = 201
        payload = registration_result(registration, event)
        record_retry(db, user_id, operation, key, "", status, payload)
    return JSONResponse(payload, status_code=status)


def organizer(event, user_id):
    if event["organizer_id"] != user_id:
        raise ApiError(403, "FORBIDDEN")


def participants(request, ids):
    if not ids:
        return {}
    query = urlencode({"id": ids}, doseq=True)
    headers = {}
    if request.headers.get("Authorization"):
        headers["Authorization"] = request.headers["Authorization"]
    if request.cookies.get("session"):
        headers["Cookie"] = f"session={request.cookies['session']}"
    url = f"http://identity:8000/internal/identity/participants?{query}"
    try:
        with urlopen(InternalRequest(url, headers=headers), timeout=3) as response:
            return {item["id"]: item for item in json.load(response)["items"]}
    except (URLError, OSError, ValueError, KeyError):
        raise ApiError(503, "SERVICE_UNAVAILABLE") from None


@router.get("/events/{identifier}/registrations")
def registrations(user_id: Viewer, request: Request, identifier: str, cursor: Cursor = None):
    scope = [user_id, "registrations", identifier]
    with db_connection() as db:
        organizer(find_event(db, identifier), user_id)
        after = read_cursor(cursor, scope)
        conditions = "AND (created_at, id) > (%s, %s)" if after else ""
        rows = db.execute(f"""
            SELECT * FROM catalog_registrations WHERE event_id = %s AND status = 'CONFIRMED'
            {conditions} ORDER BY created_at, id LIMIT %s
        """, [identifier, *(after or []), PAGE_SIZE + 1]).fetchall()
    profiles = participants(request, [row["user_id"] for row in rows[:PAGE_SIZE]])
    return page(rows, scope, lambda row: [timestamp(row["created_at"]), row["id"]],
                lambda row: {"registration": registration_dto(row), "participant": profiles.get(
                    row["user_id"], {"id": row["user_id"], "displayName": None, "avatar": None})})


@router.delete("/events/{identifier}/registrations/{registration_id}", dependencies=[Depends(empty_body)])
def remove_registration(user_id: Viewer, request: Request, identifier: str, registration_id: str):
    with db_connection() as db:
        event = find_event(db, identifier, lock=True)
        organizer(event, user_id)
        registration = db.execute("""
            SELECT * FROM catalog_registrations WHERE event_id = %s AND id = %s
        """, (identifier, registration_id)).fetchone()
        if registration is None:
            raise ApiError(404, "NOT_FOUND")
        if registration["status"] == "CONFIRMED":
            now = request_clock(request)()
            registration = db.execute("""
                UPDATE catalog_registrations SET status = 'REMOVED', removed_at = %s
                WHERE id = %s RETURNING *
            """, (now, registration_id)).fetchone()
            event = find_event(db, identifier)
            notify_change(db, identifier, now)
    return registration_result(registration, event)


@internal_router.get("/candidates")
def candidates(user_id: Viewer, request: Request, query: Annotated[CandidateQuery, Query()]):
    if query.budgetTotalMinor is not None and query.partySize is None:
        raise ApiError(400, "BAD_REQUEST")
    # Divide the budget to avoid overflow for valid bigint prices and party sizes.
    max_price = query.budgetTotalMinor // query.partySize if query.budgetTotalMinor is not None else None
    conditions, params = filtered_objects(Filters(kind=Kind(query.kind), categoryId=query.categoryId,
                                                 localDate=query.localDate, maxPriceMinor=max_price))
    order = "o.id"
    if query.kind == "EVENT":
        conditions.append("o.starts_at > %s")
        params.append(request_clock(request)())
        order = "o.starts_at, o.id"
    with db_connection() as db:
        rows = db.execute(SELECT_OBJECTS + " WHERE " + " AND ".join(conditions) + f" ORDER BY {order}",
                          params).fetchall()
    return {"items": [card(row) for row in rows]}
