import asyncio
import hashlib
import json
import logging
import secrets
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Annotated, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request as InternalRequest, urlopen
from uuid import uuid4

import redis
from fastapi import APIRouter, Depends, Header, Query, Request, Response
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from room_rules import category_weights, order_candidates, passes_threshold
from runtime import ApiError, CACHE, ENV, authenticate, connect

router = APIRouter(prefix="/v1")
PAGE_SIZE = 20
ROOM_POOL_SIZE = 10
LIFETIME = timedelta(minutes=30)
BigInt = Annotated[int, Field(ge=0, le=9223372036854775807)]
PartySize = Annotated[int, Field(ge=1, le=9223372036854775807)]
Identifier = Annotated[str, Field(min_length=1, max_length=256)]
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)]


class Kind(str, Enum):
    EVENT = "EVENT"
    PLACE = "PLACE"


class CandidateFilters(BaseModel):
    kind: Kind
    categoryId: Identifier | None = None
    localDate: date | None = None


class FeedQuery(CandidateFilters):
    budgetTotalMinor: BigInt | None = None
    partySize: PartySize | None = None
    cursor: Identifier | None = None


class Money(BaseModel):
    amountMinor: BigInt
    currency: Literal["RUB"]


class RoomFilters(CandidateFilters):
    budgetTotal: Money | None = None
    partySize: PartySize | None = None


class StartBody(BaseModel):
    filters: RoomFilters


class CreateBody(BaseModel):
    name: Annotated[str, Field(max_length=256)] | None = None


class JoinBody(BaseModel):
    token: Identifier


class VoteBody(BaseModel):
    choice: Literal["LIKE", "PASS"]


class EmptyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


def viewer(request: Request):
    return authenticate(request, complete=True)[0]


Viewer = Annotated[str, Depends(viewer)]


def db_connection():
    db = connect()
    db.row_factory = dict_row
    return db


def request_clock(request):
    override = request.headers.get("X-Dev-Swipes-Now") if ENV == "dev" else None
    if override is None:
        return lambda: datetime.now(timezone.utc)
    try:
        fixed = TypeAdapter(AwareDatetime).validate_python(override)
    except ValidationError:
        raise ApiError(422, "VALIDATION_ERROR", details={"fields": {"now": "INVALID_VALUE"}}) from None
    return lambda: fixed


def utc_timestamp(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def internal_read(request, host, path, query):
    headers = {}
    if request.headers.get("Authorization"):
        headers["Authorization"] = request.headers["Authorization"]
    elif request.cookies.get("session"):
        headers["Cookie"] = f"session={request.cookies['session']}"
    if host == "catalog" and ENV == "dev":
        now = request.headers.get("X-Dev-Catalog-Now") or request.headers.get("X-Dev-Swipes-Now")
        if now:
            headers["X-Dev-Catalog-Now"] = now
    url = f"http://{host}:8000/internal/{host}/{path}?{urlencode(query)}"
    try:
        with urlopen(InternalRequest(url, headers=headers), timeout=4) as response:
            return json.load(response)["items"]
    except HTTPError as error:
        if error.code == 401:
            raise ApiError(401, "SESSION_EXPIRED") from None
        if error.code == 400:
            raise ApiError(400, "BAD_REQUEST") from None
        if error.code == 422:
            raise ApiError(422, "VALIDATION_ERROR") from None
        raise ApiError(503, "SERVICE_UNAVAILABLE") from None
    except (URLError, OSError, ValueError, KeyError):
        raise ApiError(503, "SERVICE_UNAVAILABLE") from None


def catalog_candidates(request, filters):
    return internal_read(request, "catalog", "candidates",
                         {key: value for key, value in filters.items() if value is not None})


def room_candidates(request, filters):
    budget = filters["budgetTotal"]
    return catalog_candidates(request, {
        "kind": filters["kind"],
        "categoryId": filters["categoryId"],
        "localDate": filters["localDate"],
        "budgetTotalMinor": budget["amountMinor"] if budget else None,
        "partySize": filters["partySize"],
    })


def member(request, user_id):
    profile, = internal_read(request, "identity", "participants", {"id": user_id})
    return {"userId": user_id, "displayName": profile["displayName"]}


def feed_page(db, feed_id, items, position):
    end = position + PAGE_SIZE
    next_cursor = None
    if end < len(items):
        next_cursor = db.execute("""
            SELECT token FROM swipe_cursors WHERE feed_id = %s AND position = %s
        """, (feed_id, end)).fetchone()["token"]
    return {"items": items[position:end], "nextCursor": next_cursor}


@router.get("/feed/candidates")
def feed(request: Request, user_id: Viewer, query: Annotated[FeedQuery, Query()]):
    now = request_clock(request)()
    filters = query.model_dump(mode="json", exclude={"cursor"})
    if (query.budgetTotalMinor is not None and query.partySize is None or
            query.kind == Kind.PLACE and query.localDate is not None):
        raise ApiError(400, "BAD_REQUEST")
    if query.cursor:
        with db_connection() as db:
            record = db.execute("""
                SELECT f.*, c.position FROM swipe_cursors c
                JOIN swipe_feeds f ON f.id = c.feed_id WHERE c.token = %s AND f.user_id = %s
            """, (query.cursor, user_id)).fetchone()
            if record is None or record["expires_at"] <= now:
                raise ApiError(409, "CURSOR_EXPIRED")
            if record["filters"] != filters:
                raise ApiError(400, "BAD_REQUEST")
            return feed_page(db, record["id"], record["items"], record["position"])

    items = catalog_candidates(request, filters)
    if len(items) <= PAGE_SIZE:
        return {"items": items, "nextCursor": None}
    feed_id = str(uuid4())
    with db_connection() as db:
        # Only real time drives cleanup, so request-scoped dev time cannot affect other users.
        db.execute("DELETE FROM swipe_feeds WHERE expires_at <= CURRENT_TIMESTAMP")
        db.execute("INSERT INTO swipe_feeds VALUES (%s, %s, %s, %s, %s)",
                   (feed_id, user_id, Jsonb(filters), Jsonb(items), now + LIFETIME))
        for position in range(PAGE_SIZE, len(items), PAGE_SIZE):
            db.execute("INSERT INTO swipe_cursors VALUES (%s, %s, %s)",
                       (secrets.token_urlsafe(32), feed_id, position))
        return feed_page(db, feed_id, items, 0)


def snapshot(room, user_id):
    data = room["snapshot"]
    result = {key: data[key] for key in ("name", "ownerId", "state", "members", "filters", "result")}
    result.update(id=room["id"], version=room["version"], round=None)
    current = data["round"]
    if current:
        votes = current["votes"].get(user_id, {})
        expires_at = current.get("expiresAt") or utc_timestamp(room["expires_at"])
        result["round"] = {
            "id": current["id"], "number": current.get("number", 1),
            "expiresAt": expires_at, "memberCount": len(data["members"]),
            "finishedCount": len(current["finished"]), "candidates": current["candidates"],
            "myVotes": [{"candidate": card["ref"], "choice": votes[card["ref"]["id"]]}
                        for card in current["candidates"] if card["ref"]["id"] in votes],
            "myFinished": user_id in current["finished"],
        }
    return result


def save(db, room, changes):
    current = room["snapshot"]["round"]
    if current and current.get("expiresAt"):
        room["expires_at"] = datetime.fromisoformat(current["expiresAt"])
    room["version"] += 1
    db.execute("""
        UPDATE swipe_rooms SET version = %s, snapshot = %s, expires_at = %s WHERE id = %s
    """, (room["version"], Jsonb(room["snapshot"]), room["expires_at"], room["id"]))
    changes[room["id"]] = room["version"]


def notify(changes):
    for room_id, version in changes.items():
        try:
            CACHE.publish(f"room:{room_id}", version)
        except redis.RedisError:
            logging.warning("Room update notification unavailable")


def read_room(db, identifier, user_id, now, changes):
    room = db.execute("SELECT * FROM swipe_rooms WHERE id = %s FOR UPDATE", (identifier,)).fetchone()
    if room is None or all(member["userId"] != user_id for member in room["snapshot"]["members"]):
        raise ApiError(404, "NOT_FOUND")
    close_expired(db, room, now, changes)
    return room


def close_expired(db, room, now, changes):
    data = room["snapshot"]
    if data["state"] == "VOTING" and room["expires_at"] <= now:
        data.update(state="CLOSED", round=None)
        save(db, room, changes)


def owner_in_lobby(room, user_id):
    data = room["snapshot"]
    if data["ownerId"] != user_id:
        raise ApiError(403, "FORBIDDEN")
    if data["state"] != "LOBBY":
        raise ApiError(409, "INVALID_STATE")


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def post(user_id, operation, key, body, action):
    changes = {}
    fingerprint = digest(json.dumps(body, sort_keys=True, ensure_ascii=False))
    with db_connection() as db:
        db.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                   (json.dumps([user_id, operation, key]),))
        previous = db.execute("""
            SELECT fingerprint, response FROM swipe_retries WHERE user_id = %s AND operation = %s AND key = %s
        """, (user_id, operation, key)).fetchone()
        if previous:
            if previous["fingerprint"] != fingerprint:
                raise ApiError(409, "IDEMPOTENCY_CONFLICT")
            return previous["response"]
        response = action(db, changes)
        db.execute("INSERT INTO swipe_retries VALUES (%s, %s, %s, %s, %s)",
                   (user_id, operation, key, fingerprint, Jsonb(response)))
    notify(changes)
    return response


@router.post("/rooms", status_code=201)
def create(request: Request, user_id: Viewer, key: IdempotencyKey, body: CreateBody | None = None):
    name = body.name if body else None

    def action(db, changes):
        identifier = str(uuid4())
        data = {"ownerId": user_id, "name": name, "state": "LOBBY", "filters": None,
                "round": None, "members": [member(request, user_id)], "result": None,
                "used": [], "completions": {}}
        db.execute("INSERT INTO swipe_rooms (id, snapshot) VALUES (%s, %s)", (identifier, Jsonb(data)))
        return snapshot({"id": identifier, "version": 0, "snapshot": data}, user_id)

    return post(user_id, "create", key, {"name": name}, action)


@router.post("/rooms/{identifier}/invites", status_code=201)
def invite(request: Request, identifier: str, user_id: Viewer, key: IdempotencyKey,
           body: EmptyBody | None = None):
    clock = request_clock(request)

    def action(db, changes):
        now = clock()
        room = read_room(db, identifier, user_id, now, changes)
        owner_in_lobby(room, user_id)
        token = secrets.token_urlsafe(32)
        expires = now + LIFETIME
        db.execute("INSERT INTO swipe_invites VALUES (%s, %s, %s)", (digest(token), identifier, expires))
        return {"url": f"srastemsya://room-invites/join?token={token}",
                "expiresAt": utc_timestamp(expires)}

    return post(user_id, f"invite:{identifier}", key, {}, action)


@router.post("/room-invites/join")
def join(request: Request, user_id: Viewer, key: IdempotencyKey, body: JoinBody):
    clock = request_clock(request)

    def action(db, changes):
        invitation = db.execute("SELECT * FROM swipe_invites WHERE digest = %s",
                                (digest(body.token),)).fetchone()
        if invitation is None:
            raise ApiError(404, "NOT_FOUND")
        room = db.execute("SELECT * FROM swipe_rooms WHERE id = %s FOR UPDATE",
                          (invitation["room_id"],)).fetchone()
        now = clock()
        close_expired(db, room, now, changes)
        data = room["snapshot"]
        if any(member["userId"] == user_id for member in data["members"]):
            return snapshot(room, user_id)
        if invitation["expires_at"] <= now:
            raise ApiError(410, "INVITE_EXPIRED")
        if data["state"] != "LOBBY":
            raise ApiError(409, "INVALID_STATE")
        data["members"].append(member(request, user_id))
        save(db, room, changes)
        return snapshot(room, user_id)

    return post(user_id, "join", key, body.model_dump(mode="json"), action)


def open_round(data, items, now):
    used = set(data["used"])
    unseen = [card for card in items if card["ref"]["id"] not in used]
    weights = category_weights(data.get("history", []))
    candidates = order_candidates(unseen, weights)[:ROOM_POOL_SIZE]
    if not candidates:
        data.update(state="EXHAUSTED", round=None)
        return
    data["used"].extend(card["ref"]["id"] for card in candidates)
    number = data.get("roundNumber", 0) + 1
    data["roundNumber"] = number
    data.update(state="VOTING", round={"id": str(uuid4()), "number": number, "candidates": candidates,
                                        "expiresAt": utc_timestamp(now + LIFETIME),
                                        "votes": {}, "finished": []})


@router.post("/rooms/{identifier}/start")
def start(request: Request, identifier: str, user_id: Viewer, key: IdempotencyKey, body: StartBody):
    clock = request_clock(request)
    filters = body.filters.model_dump(mode="json")
    if filters["kind"] == "PLACE" and filters["localDate"]:
        raise ApiError(400, "BAD_REQUEST")

    def action(db, changes):
        room = read_room(db, identifier, user_id, clock(), changes)
        owner_in_lobby(room, user_id)
        data = room["snapshot"]
        if len(data["members"]) < 2:
            raise ApiError(409, "INVALID_STATE")
        data["filters"] = {**filters, "partySize": len(data["members"])}
        open_round(data, room_candidates(request, data["filters"]), clock())
        save(db, room, changes)
        return snapshot(room, user_id)

    return post(user_id, f"start:{identifier}", key, {"filters": filters}, action)


def get_round(data, round_id):
    current = data["round"]
    if current is None or current["id"] != round_id or data["state"] == "MATCHED":
        if round_id in data["completions"] or data["state"] == "VOTING":
            raise ApiError(409, "STALE_ROUND")
        raise ApiError(409, "INVALID_STATE")
    return current


def update_round(request, identifier, user_id, action):
    changes = {}
    error = None
    with db_connection() as db:
        now = request_clock(request)()
        room = read_room(db, identifier, user_id, now, changes)
        try:
            if action(room["snapshot"], now):
                save(db, room, changes)
        except ApiError as failure:
            # Expiry is a committed transition even if the requested mutation is rejected.
            error = failure
        response = snapshot(room, user_id)
    notify(changes)
    if error:
        raise error
    return response


@router.put("/rooms/{identifier}/rounds/{round_id}/votes/{kind}/{candidate_id}")
def vote(request: Request, identifier: str, round_id: str, kind: Kind, candidate_id: str,
         user_id: Viewer, body: VoteBody):
    def action(data, _now):
        current = get_round(data, round_id)
        if user_id in current["finished"]:
            raise ApiError(409, "INVALID_STATE")
        if not any(card["ref"] == {"id": candidate_id, "kind": kind.value} for card in current["candidates"]):
            raise ApiError(404, "NOT_FOUND")
        votes = current["votes"].setdefault(user_id, {})
        if votes.get(candidate_id) == body.choice:
            return False
        votes[candidate_id] = body.choice
        return True

    return update_round(request, identifier, user_id, action)


def round_summary(current, member_count):
    cards = []
    for card in current["candidates"]:
        card_id = card["ref"]["id"]
        likes = sum(votes.get(card_id) == "LIKE" for votes in current["votes"].values())
        cards.append({
            "ref": card["ref"], "categoryId": card["categoryId"],
            "likes": likes, "passes": member_count - likes,
        })
    return {"number": current.get("number", 1), "cards": cards}


def winner(cards, member_count):
    best = max(cards, key=lambda card: card["likes"])
    if passes_threshold(best["likes"], member_count):
        return best["ref"], best["likes"]
    return None


@router.put("/rooms/{identifier}/rounds/{round_id}/completion")
def finish(request: Request, identifier: str, round_id: str, user_id: Viewer,
           body: EmptyBody | None = None):
    def action(data, now):
        if user_id in data["completions"].get(round_id, []):
            return False
        current = get_round(data, round_id)
        if len(current["votes"].get(user_id, {})) != len(current["candidates"]):
            raise ApiError(409, "INVALID_STATE")
        finished = [*current["finished"], user_id]
        member_count = len(data["members"])
        if len(finished) == member_count:
            summary = round_summary(current, member_count)
            data.setdefault("history", []).append(summary)
            selected = winner(summary["cards"], member_count)
            if selected is None:
                candidates = room_candidates(request, data["filters"])
                open_round(data, candidates, now)
            else:
                candidate, likes = selected
                data.update(state="MATCHED", result={
                    "winner": candidate, "basis": "THRESHOLD", "likes": likes,
                    "memberCount": member_count,
                })
        current["finished"] = finished
        data["completions"][round_id] = finished
        return True

    return update_round(request, identifier, user_id, action)


def get_snapshot(request, identifier, clock):
    user_id = viewer(request)
    changes = {}
    with db_connection() as db:
        room = read_room(db, identifier, user_id, clock(), changes)
        result = snapshot(room, user_id)
        expires_at = room["expires_at"] if result["state"] == "VOTING" else None
    notify(changes)
    return result, expires_at


async def room_updates(request, identifier, after_version, wait_seconds):
    clock = request_clock(request)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + wait_seconds

    async def read():
        return await asyncio.to_thread(get_snapshot, request, identifier, clock)

    result, _ = await read()
    if after_version is None or result["version"] > after_version:
        return result

    client = redis.asyncio.Redis(host="redis", username=CACHE.connection_pool.connection_kwargs["username"],
                               password=CACHE.connection_pool.connection_kwargs["password"],
                               socket_connect_timeout=2, socket_timeout=2)
    try:
        async with client.pubsub() as subscription:
            await subscription.subscribe(f"room:{identifier}")
            # Redis subscribe() only sends the command. Consume its acknowledgement before reading.
            await subscription.get_message(timeout=2)
            while True:
                result, expires_at = await read()
                if result["version"] > after_version:
                    return result
                remaining = deadline - loop.time()
                if remaining <= 0:
                    return Response(status_code=204)
                if await request.is_disconnected():
                    return Response(status_code=204)
                while not await request.is_disconnected():
                    remaining = deadline - loop.time()
                    until_expiry = (expires_at - clock()).total_seconds() if expires_at else remaining
                    if min(remaining, until_expiry) <= 0:
                        break
                    if await subscription.get_message(timeout=min(remaining, until_expiry, 1)):
                        break
                else:
                    return Response(status_code=204)
    finally:
        await client.aclose()


@router.get("/rooms/{identifier}")
async def get_room(request: Request, identifier: str,
                   afterVersion: Annotated[int | None, Query(ge=0)] = None,
                   waitSeconds: Annotated[int | None, Query(ge=1, le=25)] = None):
    if waitSeconds is not None and afterVersion is None:
        await asyncio.to_thread(viewer, request)
        raise ApiError(400, "BAD_REQUEST")
    return await room_updates(request, identifier, afterVersion, waitSeconds or 25)
