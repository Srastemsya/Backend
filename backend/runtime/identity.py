import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from datetime import date, datetime, timezone
from typing import Annotated
from uuid import uuid4
from zoneinfo import ZoneInfo

import jwt
from cryptography.fernet import Fernet
from fastapi import APIRouter, Header, Query, Request, Response
from pydantic import BaseModel

from runtime import (ACCESS_TTL, AUDIENCE, CACHE, ENV, ISSUER, KEYS, MOCK,
                     SESSION_TTL, ApiError, authenticate, connect)

router = APIRouter(prefix="/v1")
internal_router = APIRouter(prefix="/internal/identity")
OTP = os.getenv("DEV_OTP", "0427")
PEPPER = os.environ.get("IDENTITY_SECRET", "").encode() or (KEYS / "identity-secret").read_bytes()
REPLAY = Fernet(base64.urlsafe_b64encode(hashlib.sha256(b"replay:" + PEPPER).digest()))
CONTACTS = [f"person{n}@example.test" for n in range(1, 11)]
DEV_CONTACTS = set(CONTACTS + ["new@example.test", "+15550100100"])


def migrate(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id text PRIMARY KEY, destination text UNIQUE NOT NULL,
            display_name text, birth_date date
        );
        CREATE TABLE IF NOT EXISTS challenges (
            id text PRIMARY KEY, destination text NOT NULL, created bigint NOT NULL,
            attempts integer NOT NULL DEFAULT 0, consumed boolean NOT NULL DEFAULT false
        );
        CREATE INDEX IF NOT EXISTS challenge_contact ON challenges(destination, created DESC);
        CREATE TABLE IF NOT EXISTS refreshes (
            verifier text PRIMARY KEY, sid text NOT NULL, account_id text NOT NULL REFERENCES accounts(id),
            expires bigint NOT NULL, used boolean NOT NULL DEFAULT false
        );
        CREATE TABLE IF NOT EXISTS retries (
            scope text NOT NULL, key text NOT NULL, fingerprint text NOT NULL,
            response bytea NOT NULL, expires bigint NOT NULL, PRIMARY KEY (scope, key)
        );
    """)
    if ENV == "dev" and MOCK:
        if not re.fullmatch(r"[0-9]{4}", OTP):
            raise RuntimeError("Invalid dev OTP format")
        from dev_fixtures import dev_account_id
        for index, destination in enumerate(CONTACTS, 1):
            db.execute("""
                INSERT INTO accounts VALUES (%s, %s, %s, DATE '1995-01-01')
                ON CONFLICT (destination) DO NOTHING
            """, (dev_account_id(index), destination, f"Участник {index}"))


class Challenge(BaseModel):
    channel: str
    destination: str


class Verify(BaseModel):
    code: str


class Refresh(BaseModel):
    refreshToken: str


class Registration(BaseModel):
    displayName: str
    birthDate: str


def digest(value):
    return hmac.new(PEPPER, value.encode(), "sha256").hexdigest()


def lock(db, scope):
    db.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (scope,))


def iso(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def retry(db, scope, key, fingerprint, now):
    if not key or len(key) > 255:
        raise ApiError(422, "VALIDATION_ERROR")
    row = db.execute("SELECT fingerprint, response FROM retries WHERE scope=%s AND key=%s AND expires>%s",
                     (scope, key, now)).fetchone()
    if row:
        if row[0] != fingerprint:
            raise ApiError(409, "IDEMPOTENCY_CONFLICT")
        return json.loads(REPLAY.decrypt(bytes(row[1])))


def remember(db, scope, key, fingerprint, result, now):
    db.execute("""
        INSERT INTO retries VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (scope, key) DO UPDATE
        SET fingerprint=excluded.fingerprint, response=excluded.response, expires=excluded.expires
    """, (scope, key, fingerprint, REPLAY.encrypt(json.dumps(result).encode()), now + 600))


def normalize(body):
    destination = body.destination.strip()
    if body.channel == "SMS":
        destination = re.sub(r"[ ().-]", "", destination)
        if not re.fullmatch(r"\+[1-9][0-9]{7,14}", destination):
            raise ApiError(422, "VALIDATION_ERROR")
    elif body.channel == "EMAIL":
        destination = destination.lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", destination):
            raise ApiError(422, "VALIDATION_ERROR")
    else:
        raise ApiError(422, "VALIDATION_ERROR")
    return destination


def limited(seconds):
    return ApiError(429, "RATE_LIMITED", {"Retry-After": str(max(1, seconds))})


@router.post("/auth/challenges", status_code=201)
def challenge(body: Challenge, key: str = Header(alias="Idempotency-Key")):
    destination = normalize(body)
    if not MOCK:
        raise ApiError(503, "SERVICE_UNAVAILABLE")
    if destination not in DEV_CONTACTS:
        raise ApiError(422, "VALIDATION_ERROR")
    scope = f"challenge:{destination}"
    fingerprint = digest(body.model_dump_json())
    now = int(time.time())
    with connect() as db:
        lock(db, scope)
        replay = retry(db, scope, key, fingerprint, now)
        if replay:
            return replay
        previous = db.execute("SELECT id, created FROM challenges WHERE destination=%s ORDER BY created DESC LIMIT 1",
                              (destination,)).fetchone()
        if previous and previous[1] + 60 > now:
            raise limited(previous[1] + 60 - now)
        challenge_id = str(uuid4())
        db.execute("UPDATE challenges SET consumed=true WHERE destination=%s AND NOT consumed", (destination,))
        db.execute("INSERT INTO challenges (id,destination,created) VALUES (%s,%s,%s)",
                   (challenge_id, destination, now))
        CACHE.set(f"otp:{challenge_id}", digest(challenge_id + OTP), ex=300)
        result = {"challengeId": challenge_id, "expiresAt": iso(now + 300), "resendAvailableAt": iso(now + 60)}
        remember(db, scope, key, fingerprint, result, now)
        return result


def issue(db, sid, user_id, complete, now, expires):
    refresh_token = secrets.token_urlsafe(48)
    access = jwt.encode({"iss": ISSUER, "aud": AUDIENCE, "sub": user_id, "sid": sid,
                         "iat": now, "exp": now + ACCESS_TTL},
                        (KEYS / "private.pem").read_text(), algorithm="RS256")
    db.execute("INSERT INTO refreshes VALUES (%s,%s,%s,%s,false)",
               (digest(refresh_token), sid, user_id, expires))
    return {"accessToken": access, "accessExpiresAt": iso(now + ACCESS_TTL), "refreshToken": refresh_token,
            "refreshExpiresAt": iso(expires), "userId": user_id, "profileComplete": complete}


@router.post("/auth/challenges/{challenge_id}/verify")
def verify(challenge_id: str, body: Verify, key: str = Header(alias="Idempotency-Key")):
    if not re.fullmatch(r"[0-9]{4}", body.code):
        raise ApiError(422, "VALIDATION_ERROR")
    now = int(time.time())
    scope = f"verify:{challenge_id}"
    fingerprint = digest(body.model_dump_json())
    with connect() as db:
        found = db.execute("SELECT destination FROM challenges WHERE id=%s", (challenge_id,)).fetchone()
        if not found:
            raise ApiError(410, "OTP_EXPIRED")
        destination = found[0]
        lock(db, f"challenge:{destination}")
        replay = retry(db, scope, key, fingerprint, now)
        if replay:
            return replay
        created, attempts, consumed = db.execute("SELECT created,attempts,consumed FROM challenges WHERE id=%s",
                                                 (challenge_id,)).fetchone()
        if consumed or created + 300 <= now:
            raise ApiError(410, "OTP_EXPIRED")
        if attempts >= 5:
            raise limited(created + 300 - now)
        expected = CACHE.get(f"otp:{challenge_id}")
        if expected is None:
            raise ApiError(410, "OTP_EXPIRED")
        if not hmac.compare_digest(expected, digest(challenge_id + body.code)):
            db.execute("UPDATE challenges SET attempts=attempts+1 WHERE id=%s", (challenge_id,))
            db.commit()
            raise ApiError(422, "OTP_INVALID")
        db.execute("UPDATE challenges SET consumed=true WHERE id=%s", (challenge_id,))
        db.execute("INSERT INTO accounts(id,destination) VALUES (%s,%s) ON CONFLICT (destination) DO NOTHING",
                   (str(uuid4()), destination))
        user_id, complete = db.execute("SELECT id,birth_date IS NOT NULL FROM accounts WHERE destination=%s",
                                       (destination,)).fetchone()
        sid = str(uuid4())
        result = issue(db, sid, user_id, complete, now, now + SESSION_TTL)
        remember(db, scope, key, fingerprint, result, now)
        with CACHE.pipeline() as updates:
            updates.set(f"auth:session:{sid}", user_id, ex=SESSION_TTL)
            if complete:
                updates.set(f"auth:profile:{user_id}", "complete")
            updates.execute()
        return result


@router.post("/auth/refresh")
def refresh(body: Refresh, key: str = Header(alias="Idempotency-Key")):
    now = int(time.time())
    fingerprint = digest(body.refreshToken)
    with connect() as db:
        row = db.execute("SELECT sid,account_id,expires FROM refreshes WHERE verifier=%s", (fingerprint,)).fetchone()
        if not row:
            raise ApiError(401, "UNAUTHENTICATED")
        sid, user_id, expires = row
        scope = f"refresh:{sid}"
        lock(db, scope)
        if expires <= now or CACHE.get(f"auth:session:{sid}") != user_id:
            raise ApiError(401, "SESSION_EXPIRED")
        replay = retry(db, scope, key, fingerprint, now)
        if replay:
            return replay
        used, = db.execute("SELECT used FROM refreshes WHERE verifier=%s", (fingerprint,)).fetchone()
        if used:
            CACHE.delete(f"auth:session:{sid}")
            raise ApiError(401, "SESSION_EXPIRED")
        db.execute("UPDATE refreshes SET used=true WHERE verifier=%s", (fingerprint,))
        complete, = db.execute("SELECT birth_date IS NOT NULL FROM accounts WHERE id=%s", (user_id,)).fetchone()
        result = issue(db, sid, user_id, complete, now, expires)
        remember(db, scope, key, fingerprint, result, now)
        return result


def profile(db, user_id):
    row = db.execute("SELECT display_name,birth_date FROM accounts WHERE id=%s", (user_id,)).fetchone()
    if not row:
        raise ApiError(401, "SESSION_EXPIRED")
    name, birthday = row
    return {"id": user_id, "profileComplete": birthday is not None, "displayName": name,
            "birthDate": birthday, "city": None, "bio": None, "avatar": None,
            "stats": {"eventsCount": 0, "roomsCount": 0}}


@router.get("/me")
def me(request: Request):
    user_id, _ = authenticate(request)
    with connect() as db:
        return profile(db, user_id)


@router.put("/me/registration")
def register(request: Request, body: Registration):
    user_id, _ = authenticate(request)
    name = body.displayName.strip()
    try:
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", body.birthDate):
            raise ValueError
        birthday = date.fromisoformat(body.birthDate)
    except ValueError:
        raise ApiError(422, "VALIDATION_ERROR") from None
    if not 1 <= len(name) <= 100 or birthday > datetime.now(ZoneInfo("Asia/Vladivostok")).date():
        raise ApiError(422, "VALIDATION_ERROR")
    with connect() as db:
        db.execute("UPDATE accounts SET display_name=%s,birth_date=%s WHERE id=%s", (name, birthday, user_id))
        result = profile(db, user_id)
    CACHE.set(f"auth:profile:{user_id}", "complete")
    return result


@router.delete("/auth/session", status_code=204)
def logout(request: Request):
    _, sid = authenticate(request)
    with connect() as db:
        lock(db, f"refresh:{sid}")
        CACHE.delete(f"auth:session:{sid}")
    return Response(status_code=204)


@internal_router.get("/participants")
def participants(request: Request, id: Annotated[list[str], Query(min_length=1, max_length=20)]):
    authenticate(request, complete=True)
    with connect() as db:
        rows = db.execute("SELECT id, display_name FROM accounts WHERE id = ANY(%s)", (id,)).fetchall()
    return {"items": [{"id": user_id, "displayName": name, "avatar": None} for user_id, name in rows]}
