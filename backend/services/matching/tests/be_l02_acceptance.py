#!/usr/bin/env python3
"""BE-L02 black-box acceptance: round pool of at most 10 cards and Round.number.

Verifies AC-01..AC-06 of reports/BE-L02/acceptance.md against an isolated
Compose stand through Nginx. Public HTTP API, published dev data and public
documents only: no application sources, no internal state.

Expected card order is derived from the contracts (for EVENT: startsAt, id)
and the published stand data described in backend/README.md.

Environment:
  BE_L02_BASE_URL         base URL via Nginx (default http://127.0.0.1:18092)
  BE_L02_OTP              dev OTP (default 0427)
  BE_L02_COMPOSE_PROJECT  Compose project; enables the restart guarantee test
"""
import datetime
import json
import os
import re
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor

BASE = os.environ.get("BE_L02_BASE_URL", "http://127.0.0.1:18092").rstrip("/")
OTP = os.environ.get("BE_L02_OTP", "0427")
PROJECT = os.environ.get("BE_L02_COMPOSE_PROJECT", "")
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
REPO = os.path.dirname(BACKEND)

EVENT_IDS = ["dev-swipe-event-%02d" % n for n in range(1, 23)]
PLACE_IDS = ["dev-swipe-place-%02d" % n for n in range(1, 23)]
MIX_IDS = ["dev-lobby-mix-%02d" % n for n in range(1, 36)]
SHORT_IDS = ["dev-lobby-short-%02d" % n for n in range(1, 5)]
TWO_IDS = ["dev-lobby-two-%02d" % n for n in range(1, 15)]
EVENT_FILTERS = {"kind": "EVENT", "categoryId": "dev-swipe-events"}
PLACE_FILTERS = {"kind": "PLACE", "categoryId": "dev-swipe-places"}
SHORT_FILTERS = {"kind": "EVENT", "categoryId": "dev-lobby-short"}
TWO_FILTERS = {"kind": "EVENT", "categoryId": "dev-lobby-two"}
MIX_FILTERS = {"kind": "EVENT", "localDate": "2090-02-01"}

TOKENS = {}
CLOCK = None


def api(path, method="GET", body=None, token=None, headers=None, timeout=45):
    data = None
    head = {"Content-Type": "application/json"}
    if method in ("POST", "PUT", "DELETE"):
        head["Idempotency-Key"] = str(uuid.uuid4())
    if headers:
        head.update(headers)
    if CLOCK:
        head["X-Dev-Swipes-Now"] = CLOCK
    if body is not None:
        data = json.dumps(body).encode()
    if token:
        head["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + path, data=data, headers=head, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            payload = json.loads(raw) if raw else None
        except ValueError:
            payload = {"raw": raw[:120].decode("utf-8", "replace")}
        return exc.code, payload, dict(exc.headers)


def call(path, method="GET", body=None, token=None, status=200, code=None,
         headers=None, key=None, timeout=45):
    extra = dict(headers or {})
    if key:
        extra["Idempotency-Key"] = key
    got, payload, resp_headers = api(path, method, body, token, extra, timeout)
    assert got == status, "%s %s -> %s, expected %s (%s)" % (
        method, path.split("?")[0], got, status,
        (payload or {}).get("error", {}).get("code"))
    if status == 204:
        assert payload is None, "204 carried a body"
    if code is not None:
        observed = (payload or {}).get("error", {}).get("code")
        assert observed == code, "%s %s -> %s, expected %s" % (
            method, path.split("?")[0], observed, code)
    return payload, resp_headers


def login(email):
    """Dev login with the synthetic OTP, tolerating the 60s resend window."""
    deadline = time.time() + 200
    while True:
        status, payload, headers = api(
            "/v1/auth/challenges", "POST",
            {"channel": "EMAIL", "destination": email})
        if status == 429:
            if time.time() > deadline:
                raise AssertionError("challenge rate limited for %s" % email)
            try:
                delay = float(headers.get("Retry-After", "61"))
            except ValueError:
                delay = 61.0
            time.sleep(max(1.0, min(delay + 1, deadline - time.time())))
            continue
        assert status == 201, "challenge %s -> %s %s" % (email, status, payload)
        break
    status, session, _ = api(
        "/v1/auth/challenges/%s/verify" % payload["challengeId"], "POST",
        {"code": OTP})
    assert status == 200, "verify %s -> %s %s" % (email, status, session)
    assert session["profileComplete"], "%s profile is incomplete" % email
    TOKENS[email] = session["accessToken"]
    return session


def token(email):
    if email not in TOKENS:
        login(email)
    return TOKENS[email]


def person(n):
    return "person%d@example.test" % n


def query(path, **params):
    return path + "?" + urllib.parse.urlencode(params)


def feed(who, **params):
    return call(query("/v1/feed/candidates", **params), token=token(who))[0]


def all_feed_ids(who, **params):
    """Walk every page of a feed and return the ordered card ids."""
    seen, cursor, pages = [], None, 0
    while True:
        page = feed(who, cursor=cursor, **params) if cursor else feed(who, **params)
        pages += 1
        assert pages < 20, "feed pagination did not terminate"
        batch = [card["ref"]["id"] for card in page["items"]]
        assert len(batch) <= 20, "single feed page exceeded 20 cards"
        assert not set(batch) & set(seen), "feed pages overlap"
        seen.extend(batch)
        cursor = page["nextCursor"]
        if cursor is None:
            return seen


def create_room(who, name="BE-L02 acceptance"):
    return call("/v1/rooms", "POST", {"name": name}, token(who), 201)[0]


def invite_token(who, room):
    payload = call("/v1/rooms/%s/invites" % room["id"], "POST",
                   token=token(who), status=201)[0]
    return urllib.parse.parse_qs(
        urllib.parse.urlparse(payload["url"]).query)["token"][0]


def join(who, tok, status=200, code=None):
    return call("/v1/room-invites/join", "POST", {"token": tok},
                token(who), status, code)[0]


def room_of(who, room, **params):
    path = "/v1/rooms/%s" % room["id"]
    if params:
        path = query(path, **params)
    return call(path, token=token(who))[0]


def start_room(who, room, filters):
    body = {"filters": dict(filters)}
    body["filters"].setdefault("budgetTotal", None)
    return call("/v1/rooms/%s/start" % room["id"], "POST", body,
                token(who))[0]


def vote(who, room, card_id, choice="PASS", kind="EVENT", status=200, code=None):
    path = "/v1/rooms/%s/rounds/%s/votes/%s/%s" % (
        room["id"], room["round"]["id"], kind, card_id)
    return call(path, "PUT", {"choice": choice}, token(who), status, code)[0]


def complete(who, room, status=200, code=None):
    path = "/v1/rooms/%s/rounds/%s/completion" % (room["id"], room["round"]["id"])
    return call(path, "PUT", {}, token(who), status, code)[0]


def card_ids(room):
    return [card["ref"]["id"] for card in room["round"]["candidates"]]


def roster(room):
    return [member["userId"] for member in room["members"]]


def build_room(members, filters, owner=None):
    """Create a room, invite the members, start it and return the snapshot."""
    owner = owner or members[0]
    room = create_room(owner)
    tok = invite_token(owner, room)
    for who in members[1:]:
        room = join(who, tok)
    return start_room(owner, room, filters), tok


def pass_round(members, room, likes=None):
    """Every member passes every card (except liked ones) and completes."""
    likes = likes or {}
    for who in members:
        for index, card_id in enumerate(card_ids(room)):
            vote(who, room, card_id,
                 "LIKE" if index in likes.get(who, ()) else "PASS")
        complete(who, room)
    return room_of(members[0], room)


def compose(*args):
    command = ["docker", "compose", "-p", PROJECT,
               "-f", "compose.yaml", "-f", "compose.dev.yaml"] + list(args)
    proc = subprocess.run(command, cwd=BACKEND, capture_output=True, timeout=420)
    assert proc.returncode == 0, "compose %s exited %s" % (args[0], proc.returncode)
    return proc.stdout.decode()


def wait_swipes():
    for _ in range(60):
        try:
            call("/swipes/health")
            return
        except AssertionError:
            time.sleep(1)
    raise AssertionError("swipes did not become ready")


def ac01_02():
    members = [person(n) for n in range(1, 5)]
    room, invitation = build_room(members, EVENT_FILTERS)
    call("/v1/rooms/" + room["id"], token=token(person(5)), status=404, code="NOT_FOUND")
    join(person(5), invitation, status=409, code="INVALID_STATE")
    for number in range(1, 4):
        expected = EVENT_IDS[(number - 1) * 10:number * 10]
        for who in members:
            snapshot = room_of(who, room)
            assert snapshot["round"]["number"] == number
            assert card_ids(snapshot) == expected, card_ids(snapshot)
            assert roster(snapshot) == roster(room) and len(roster(snapshot)) == 4
        room = pass_round(members, room)
    assert room["state"] == "EXHAUSTED" and room["round"] is None and room["result"] is None


def ac03():
    page = feed(person(1), **EVENT_FILTERS)
    assert [card["ref"]["id"] for card in page["items"]] == EVENT_IDS[:20]
    assert page["nextCursor"]
    page = feed(person(1), cursor=page["nextCursor"], **EVENT_FILTERS)
    assert [card["ref"]["id"] for card in page["items"]] == EVENT_IDS[20:]
    assert page["nextCursor"] is None


def d03_04():
    owner, other = person(1), person(2)
    room, _ = build_room([owner, other], SHORT_FILTERS)
    complete(owner, room, status=409, code="INVALID_STATE")
    vote(owner, room, SHORT_IDS[0], "LIKE")
    for card in SHORT_IDS:
        vote(owner, room, card)
    completed = complete(owner, room)
    vote(owner, room, SHORT_IDS[0], "LIKE", status=409, code="INVALID_STATE")
    restored = room_of(owner, room)
    assert restored["round"]["myFinished"] and restored["round"]["myVotes"] == completed["round"]["myVotes"]
    assert len(restored["round"]["myVotes"]) == 4
    assert all(v["choice"] == "PASS" for v in restored["round"]["myVotes"])
    assert room_of(other, room)["round"]["myVotes"] == []


def poll(who, room, seconds, status=200, code=None):
    return call(query("/v1/rooms/" + room["id"], afterVersion=room["version"], waitSeconds=seconds),
                token=token(who), status=status, code=code)[0]


def d03_08_09():
    owner, other = person(1), person(2)
    room = create_room(owner)
    invitation = invite_token(owner, room)
    room = room_of(owner, room)
    token(other)
    with ThreadPoolExecutor() as pool:
        pending = pool.submit(poll, owner, room, 8)
        time.sleep(.4)
        join(other, invitation)
        observed = pending.result()
        assert observed["version"] > room["version"] and len(roster(observed)) == 2
        assert invitation not in json.dumps(observed)
        room = start_room(owner, room, SHORT_FILTERS)
        pending = pool.submit(poll, owner, room, 8)
        time.sleep(.4)
        written = vote(other, room, SHORT_IDS[0], "LIKE")
        observed = pending.result()
        assert observed["version"] == written["version"] > room["version"]
        assert observed["round"]["myVotes"] == []
        start = time.monotonic()
        assert poll(owner, room, 8) == observed and time.monotonic() - start < 2


def d03_10():
    owner, outsider = person(1), person(5)
    room = create_room(owner)
    start = time.monotonic()
    poll(owner, room, 25, 204)
    assert 23 <= time.monotonic() - start < 34
    poll(owner, room, 1, 204)
    start = time.monotonic()
    poll(outsider, room, 8, 404, "NOT_FOUND")
    assert time.monotonic() - start < 2
    with ThreadPoolExecutor() as pool:
        pending = pool.submit(poll, owner, room, 4, 401, "SESSION_EXPIRED")
        time.sleep(.4)
        call("/v1/auth/session", "DELETE", token=token(owner), status=204)
        pending.result()
    del TOKENS[owner]


def int01():
    routes = [("/v1/feed/candidates?kind=EVENT", "GET", None),
              ("/v1/rooms", "POST", {"name": "protected"}),
              ("/v1/catalog/categories", "GET", None)]
    for path, method, body in routes:
        call(path, method, body, status=401, code="UNAUTHENTICATED")
    contact = "new@example.test"
    challenge = call("/v1/auth/challenges", "POST", {"channel": "EMAIL", "destination": contact}, status=201)[0]
    session = call("/v1/auth/challenges/" + challenge["challengeId"] + "/verify", "POST", {"code": OTP})[0]
    assert not session["profileComplete"]
    for path, method, body in routes:
        call(path, method, body, session["accessToken"], status=403, code="PROFILE_INCOMPLETE")


def int02():
    for service in ("swipes", "identity", "catalog"):
        compose("stop", service + "-db")
        try:
            deadline = time.monotonic() + 20
            while True:
                status, payload, _ = api("/" + service + "/health", timeout=8)
                if status == 503:
                    assert not re.search(r"postgres(?:ql)?://|password", json.dumps(payload), re.I)
                    break
                assert time.monotonic() < deadline, (service, status)
                time.sleep(.5)
        finally:
            compose("start", service + "-db")
        deadline = time.monotonic() + 30
        while api("/" + service + "/health", timeout=8)[0] != 200:
            assert time.monotonic() < deadline, service
            time.sleep(.5)
        assert not re.search(r"postgres(?:ql)?://[^ ]+:[^ ]+@", compose("logs", "--since", "1m", service))


def ac06():
    global CLOCK
    owner, other, third, fourth = [person(n) for n in range(1, 5)]
    members = [owner, other, third, fourth]
    key = uuid.uuid4().hex
    first = call("/v1/rooms", "POST", {"name": "replay"}, token(owner), 201, key=key)[0]
    assert call("/v1/rooms", "POST", {"name": "replay"}, token(owner), 201, key=key)[0] == first
    CLOCK = "2089-12-01T00:00:00Z"
    try:
        room, _ = build_room(members, TWO_FILTERS)
        assert card_ids(room) == TWO_IDS[:10]
        CLOCK = "2089-12-01T00:15:00Z"
        second = pass_round(members, room, {owner: (9,), other: (9,)})
        assert second["state"] == "VOTING" and card_ids(second) == TWO_IDS[10:]
        assert second["version"] > room["version"]
        CLOCK = "2089-12-01T00:29:59Z"
        assert room_of(owner, room)["state"] == "VOTING"
        CLOCK = "2089-12-01T00:30:00Z"
        closed = room_of(owner, room)
        assert closed["state"] == "CLOSED" and closed["round"] is None and closed["result"] is None
    finally:
        CLOCK = None
    room, _ = build_room(members, SHORT_FILTERS)
    exhausted = pass_round(members, room, {owner: (0,), other: (0,)})
    assert exhausted["state"] == "EXHAUSTED"
    assert exhausted["round"] is None and exhausted["result"] is None
    empty, _ = build_room(members, dict(EVENT_FILTERS, budgetTotal={"amountMinor": 0, "currency": "RUB"}))
    assert empty["state"] == "EXHAUSTED" and empty["round"] is None
    room, _ = build_room(members, SHORT_FILTERS)
    for who in members:
        for i, card in enumerate(SHORT_IDS):
            vote(who, room, card, "LIKE" if i == 2 and who != fourth else "PASS")
    current = room_of(owner, room)
    with ThreadPoolExecutor() as pool:
        snapshots = list(pool.map(lambda who: complete(who, room), members))
    matched = room_of(owner, room)
    assert matched["state"] == "MATCHED" and matched["result"]["winner"]["id"] == SHORT_IDS[2]
    assert matched["version"] > current["version"]
    assert all(s["result"] in (None, matched["result"]) for s in snapshots)
    assert complete(owner, room) == matched
    compose("restart", "swipes")
    wait_swipes()
    assert room_of(owner, room) == matched


def l01():
    owner = person(1)
    for n in range(1, 11):
        profile = call("/v1/me", token=token(person(n)))[0]
        assert profile["profileComplete"]
    assert all_feed_ids(owner, **MIX_FILTERS) == MIX_IDS
    page = feed(owner, **MIX_FILTERS)
    cards = page["items"] + feed(owner, cursor=page["nextCursor"], **MIX_FILTERS)["items"]
    for number, card in enumerate(cards, 1):
        suffix = ("a" if number % 2 else "b") if number <= 10 else "abc"[(number - 11) % 3]
        assert card["categoryId"] == "dev-lobby-" + suffix
    assert all_feed_ids(owner, **SHORT_FILTERS) == SHORT_IDS
    assert all_feed_ids(owner, **TWO_FILTERS) == TWO_IDS
    compose("up", "-d", "--wait")
    for service in ("identity", "catalog", "swipes"):
        call("/" + service + "/health")
    assert all_feed_ids(owner, **PLACE_FILTERS) == PLACE_IDS
    assert all_feed_ids(owner, **EVENT_FILTERS) == EVENT_IDS


def upgrade():
    global BASE
    destination = BASE
    BASE = os.environ["BE_L02_PRIOR_URL"]
    members = [person(n) for n in range(1, 6)]
    ids = {}
    for who in members:
        ids[who] = call("/v1/me", token=token(who))[0]["id"]
    assert len(set(ids.values())) == 5
    BASE = destination
    command = ["docker", "compose", "-p", PROJECT, "-f", "compose.yaml",
               "-f", "compose.dev.yaml", "up", "--build", "-d", "--wait"]
    upgraded = subprocess.run(command, cwd=BACKEND, capture_output=True, timeout=420)
    assert upgraded.returncode == 0, "prior-volume upgrade failed"
    for service in ("identity", "catalog", "swipes"):
        call("/" + service + "/health")
    for who in members:
        assert call("/v1/me", token=token(who))[0]["id"] == ids[who]
    for who in members:
        del TOKENS[who]
    assert login(members[0])["userId"] == ids[members[0]]


def ac05():
    from pathlib import Path

    root = Path(REPO)
    mobile = (root / "docs/contracts/mobile-api.md").read_text()
    discovery = (root / "docs/contracts/discovery-v1.md").read_text()
    lobby = (root / "docs/contracts/lobby-v2.md").read_text()
    readme = (root / "backend/README.md").read_text()
    dto = next(line for line in mobile.splitlines() if line.startswith("`Round = "))
    assert re.search(r"id, number, memberCount, finishedCount, candidates:", dto)
    assert "myVotes:" in dto and "myFinished:" in dto and "начиная с 1" in dto
    assert "Максимум 10 карточек в раунде" in discovery
    assert "не больше 10 карточек" in readme and "начиная с 1" in readme
    assert "## DTO" in lobby and "## Пул раунда" in lobby
    assert "lobby-v2.md#пул-раунда" in discovery and "lobby-v2.md#dto" in discovery
    for relative in ("backend/README.md", "docs/contracts/mobile-api.md", "docs/contracts/discovery-v1.md"):
        path = root / relative
        for link in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if "://" in link:
                continue
            target, _, anchor = link.partition("#")
            destination = path.parent / target if target else path
            assert destination.is_file(), (relative, link)
            if anchor:
                slugs = {
                    re.sub(r"[^\w -]", "", heading.lower()).replace(" ", "-")
                    for heading in re.findall(r"^#+ (.+)$", destination.read_text(), re.M)
                }
                assert anchor in slugs, (relative, link)



if __name__ == "__main__":
    cases = {"AC-01/02 + D03-03": ac01_02, "AC-03": ac03,
             "D03-04": d03_04, "D03-08/09": d03_08_09, "INT-01": int01,
             "INT-02": int02, "AC-05": ac05, "AC-06": ac06, "BE-L01": l01, "D03-10": d03_10}
    if "upgrade" in sys.argv[1:]:
        cases["BE-L01 prior-volume continuity"] = upgrade
    failed = 0
    for label, check in cases.items():
        if sys.argv[1:] and check.__name__ not in sys.argv[1:]:
            continue
        try:
            check()
        except Exception as error:
            print("FAIL", label, type(error).__name__, str(error), flush=True)
            failed += 1
        else:
            print("PASS", label, flush=True)
    sys.exit(bool(failed))
