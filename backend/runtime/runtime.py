import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import jwt
import psycopg
import redis
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.exceptions import HTTPException

SERVICE = os.environ["SERVICE"]
ENV = os.getenv("APP_ENV", "production")
MOCK = os.getenv("MOCK_OTP", "false") == "true"
DSN = os.environ["DATABASE_URL"]
KEYS = Path("/keys")
REDIS_CREDENTIALS = KEYS if SERVICE == "identity" else Path("/redis-key")
CACHE = redis.Redis(host="redis", username=SERVICE,
                    password=(REDIS_CREDENTIALS / "redis-password").read_text(),
                    decode_responses=True, socket_timeout=2)
AUDIENCE = "srastemsya-mobile"
ISSUER = "srastemsya-identity"
ACCESS_TTL = 900
SESSION_TTL = 30 * 86400


class ApiError(Exception):
    def __init__(self, status, code, headers=None, details=None):
        self.status = status
        self.code = code
        self.headers = headers
        self.details = details


def connect():
    return psycopg.connect(DSN, connect_timeout=2)


def readiness():
    try:
        with connect() as db:
            db.execute("SELECT 1")
    except psycopg.Error:
        return "db"
    try:
        CACHE.ping()
    except redis.RedisError:
        return "redis"
    return None


@asynccontextmanager
async def lifespan(app):
    if MOCK and ENV != "dev":
        raise RuntimeError("Mock OTP requires dev")
    with connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS schema_versions (version integer PRIMARY KEY)")
        if SERVICE == "identity":
            from identity import migrate
            migrate(db)
        if SERVICE == "catalog":
            from catalog_schema import migrate, seed
            migrate(db)
            if ENV == "dev":
                seed(db)
        db.execute("INSERT INTO schema_versions VALUES (1) ON CONFLICT DO NOTHING")
    reason = readiness()
    logging.warning("%s v1 env=%s db_host=%s readiness=%s kafka=compose-managed",
                    SERVICE, ENV, psycopg.conninfo.conninfo_to_dict(DSN)["host"], reason or "ready")
    yield


app = FastAPI(lifespan=lifespan)


@app.exception_handler(ApiError)
async def api_error(request, error):
    payload = {"code": error.code, "message": error.code, "requestId": str(uuid4())}
    if error.details is not None:
        payload["details"] = error.details
    return JSONResponse({"error": payload}, status_code=error.status, headers=error.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(request, error):
    fields = {str(entry["loc"][-1]): "INVALID_VALUE" for entry in error.errors()}
    return await api_error(request, ApiError(422, "VALIDATION_ERROR", details={"fields": fields}))


@app.exception_handler(HTTPException)
async def http_error(request, error):
    return await api_error(request, ApiError(error.status_code, "NOT_FOUND" if error.status_code == 404 else "METHOD_NOT_ALLOWED"))


async def dependency_error(request, error):
    return await api_error(request, ApiError(503, "SERVICE_UNAVAILABLE"))


app.add_exception_handler(psycopg.Error, dependency_error)
app.add_exception_handler(redis.RedisError, dependency_error)


@app.get("/health")
def health():
    reason = readiness()
    if reason:
        return JSONResponse({"status": "error", "reason": reason}, status_code=503)
    return {"status": "ok"}


@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request):
    try:
        key = os.environ["ADMIN_JWT_KEY"]
        jwt.decode(bearer(request), key, algorithms=["HS256"], audience="srastemsya-admin",
                   options={"require": ["exp", "aud"]})
    except (KeyError, jwt.InvalidTokenError):
        raise ApiError(401, "UNAUTHENTICATED") from None
    return f"<h1>{SERVICE}</h1><p>{readiness() or 'ready'}</p>"


def bearer(request):
    kind, _, token = request.headers.get("Authorization", "").partition(" ")
    return token if kind.lower() == "bearer" else ""


def authenticate(request, complete=False):
    token = bearer(request)
    if not token:
        token = request.cookies.get("session", "")
        if token and request.method not in {"GET", "HEAD", "OPTIONS"}:
            import secrets
            csrf = request.cookies.get("csrf", "")
            if not csrf or not secrets.compare_digest(csrf, request.headers.get("X-CSRF-Token", "")):
                raise ApiError(403, "FORBIDDEN")
    try:
        claims = jwt.decode(token, (KEYS / "public.pem").read_text(), algorithms=["RS256"],
                            issuer=ISSUER, audience=AUDIENCE,
                            options={"require": ["iss", "aud", "sub", "sid", "iat", "exp"]})
    except jwt.ExpiredSignatureError:
        raise ApiError(401, "SESSION_EXPIRED") from None
    except jwt.InvalidTokenError:
        raise ApiError(401, "UNAUTHENTICATED") from None
    sid = claims["sid"]
    user_id = claims["sub"]
    if CACHE.get(f"auth:session:{sid}") != user_id:
        raise ApiError(401, "SESSION_EXPIRED")
    if complete and CACHE.get(f"auth:profile:{user_id}") != "complete":
        raise ApiError(403, "PROFILE_INCOMPLETE")
    return user_id, sid


if SERVICE == "identity":
    from identity import router
    app.include_router(router)
else:
    if SERVICE == "catalog":
        from catalog import router
        app.include_router(router)

    @app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    def access_gate(request: Request, path: str):
        authenticate(request, complete=True)
        if SERVICE == "swipes" and path == "rooms" and request.method == "GET":
            return {"items": [], "nextCursor": None}
        raise ApiError(404, "NOT_FOUND")
