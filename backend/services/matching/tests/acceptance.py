"""BE-D03 contract tests. Run against an isolated Compose project."""
import datetime as dt
from concurrent.futures import ThreadPoolExecutor
import json
import os
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen
from uuid import uuid4


BASE = os.getenv("MATCHING_TEST_URL", "http://127.0.0.1:18088")
PROJECT = os.getenv("MATCHING_TEST_PROJECT", "srastemsya_d03test")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
USERS = []
CLOCK = None


def check(condition, label):
    if not condition:
        raise AssertionError(label)


def request(method, path, user=None, body=None, status=200, error=None, key=None):
    headers = {}
    if CLOCK:
        headers["X-Dev-Swipes-Now"] = CLOCK
    if user:
        headers["Authorization"] = "Bearer " + user["accessToken"]
    if method == "POST":
        headers["Idempotency-Key"] = key or uuid4().hex
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = Request(BASE + (path if path == "/swipes/health" else "/v1" + path), data=data, headers=headers, method=method)
    try:
        response = urlopen(req, timeout=38)
    except HTTPError as exc:
        response = exc
    with response:
        raw = response.read()
        check(response.status == status, f"{method} {path.split('?')[0]} expected {status}, received {response.status}")
        if status == 204:
            check(raw == b"", "204 response had a body")
            return None
        result = json.loads(raw)
    if error:
        observed = result.get("error", {}).get("code")
        check(observed == error, f"expected {error}, received {observed}")
    return result


def register(destination):
    challenge = request("POST", "/auth/challenges", body={"channel": "EMAIL", "destination": destination}, status=201)
    session = request("POST", f"/auth/challenges/{challenge['challengeId']}/verify", body={"code": os.getenv("MATCHING_TEST_OTP", "0427")})
    return session


def complete_registration(session):
    profile = request("PUT", "/me/registration", session, {"displayName": "Acceptance", "birthDate": "1997-04-15"})
    check(profile["profileComplete"], "registration incomplete")


def query(path, user, **params):
    return request("GET", f"{path}?{urlencode(params)}", user)


def compose(*args):
    command = ["docker", "compose", "-p", PROJECT, "-f", "compose.yaml", "-f", "compose.dev.yaml", *args]
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=300)
    check(proc.returncode == 0, f"Compose {args[0]} exited {proc.returncode}")
    return proc.stdout.decode()


def refs(page):
    return [(item["ref"]["kind"], item["ref"]["id"]) for item in page]


def price(amount):
    return {"amountMinor": amount, "currency": "RUB"}


def publish(user, amount, local_day, category, minute):
    begins = dt.datetime.combine(local_day, dt.time(12), dt.timezone(dt.timedelta(hours=10))) + dt.timedelta(minutes=minute)
    return request("POST", "/events", user, {
        "title": f"D03 acceptance {uuid4().hex[:8]}",
        "description": "Synthetic acceptance fixture",
        "categoryId": category,
        "startsAt": begins.isoformat(),
        "timeZone": "Asia/Vladivostok",
        "admission": {"type": "OPEN"},
        "price": price(amount) if amount is not None else None,
        "location": {"latitude": 43.12, "longitude": 131.89, "address": "Acceptance fixture"},
    }, 201)["id"]


def feed(user, **params):
    return query("/feed/candidates", user, **params)


def fixture(size, amounts=None):
    user = USERS[0]
    categories = request("GET", "/catalog/categories", user)["items"]
    category = next(item["id"] for item in categories if "EVENT" in item["kinds"])
    local_day = dt.date.today() + dt.timedelta(days=365 + int(uuid4().hex[:5], 16) % 5000)
    ids = [publish(user, None if amounts is None else amounts[i], local_day, category, i) for i in range(size)]
    return {"kind": "EVENT", "localDate": local_day.isoformat(), "categoryId": category}, ids


def invite(owner, room):
    invite_response = request("POST", f"/rooms/{room['id']}/invites", owner, status=201)
    return parse_qs(urlparse(invite_response["url"]).query)["token"][0]


def join(token, user, status=200, error=None):
    return request("POST", "/room-invites/join", user, {"token": token}, status=status, error=error)


def lobby(count=4):
    room = request("POST", "/rooms", USERS[0], {"name": "BE-D03 acceptance"}, status=201)
    token = invite(USERS[0], room)
    for user in USERS[1:count]:
        room = join(token, user)
    return room, token


def start(room, filters):
    return request("POST", f"/rooms/{room['id']}/start", USERS[0], {"filters": {"budgetTotal": None, **filters}})


def get(room, user, **kwargs):
    return request("GET", f"/rooms/{room['id']}", user, **kwargs)


def round_path(room):
    return f"/rooms/{room['id']}/rounds/{room['round']['id']}"


def vote(room, user, ref, choice="PASS", **kwargs):
    return request("PUT", f"{round_path(room)}/votes/{ref[0]}/{ref[1]}", user, {"choice": choice}, **kwargs)


def finish(room, user, **kwargs):
    return request("PUT", f"{round_path(room)}/completion", user, **kwargs)


def cards(room):
    return refs(room["round"]["candidates"])


def roster(room):
    return [person["userId"] for person in room["members"]]


def poll(room, user, wait=25, **kwargs):
    return request("GET", f"/rooms/{room['id']}?afterVersion={room['version']}&waitSeconds={wait}", user, **kwargs)


def fill(room, user, likes=()):
    for idx, ref in enumerate(cards(room)):
        vote(room, user, ref, "LIKE" if idx in likes else "PASS")


def pending_poll(pool, room, user, wait=25, **kwargs):
    future = pool.submit(poll, room, user, wait, **kwargs)
    time.sleep(0.35)
    check(not future.done(), "poll did not wait on its current version")
    return future


def test_budget():
    filters, ids = fixture(3, [100, 101, None])
    bounded = feed(USERS[0], **filters, partySize=2, budgetTotalMinor=200)
    check(refs(bounded["items"]) == [("EVENT", ids[0])], "event budget boundary or unknown price")
    unbounded = feed(USERS[0], **filters)
    check(set(refs(unbounded["items"])) == {("EVENT", item) for item in ids}, "unbounded event prices")
    place_filters = {"kind": "PLACE", "categoryId": "dev-swipe-places"}
    places = feed(USERS[0], **place_filters)
    check(places["nextCursor"], "place fixture has no second page")
    tail = feed(USERS[0], **place_filters, cursor=places["nextCursor"])
    check(("PLACE", "dev-swipe-place-22") in refs(tail["items"]), "unbounded place omitted unknown price")
    bounded_places = feed(USERS[0], **place_filters, partySize=2, budgetTotalMinor=1000)
    check(refs(bounded_places["items"]) == [("PLACE", "dev-swipe-place-21")], "place kind or budget boundary")


def test_pagination(filters, ids):
    page = feed(USERS[0], **filters)
    initial_cursor = page["nextCursor"]
    check(initial_cursor is not None, "expected multiple feed pages")
    fresh = publish(USERS[0], None, dt.date.fromisoformat(filters["localDate"]), filters["categoryId"], -1)
    seen = []
    while True:
        group = refs(page["items"])
        check(0 < len(group) <= 20 and len(group) == len(set(group)), "invalid page size or duplicate cards")
        check(not set(group).intersection(seen), "pages overlap")
        seen.extend(group)
        cursor = page["nextCursor"]
        if cursor is None:
            break
        page = feed(USERS[0], **filters, cursor=cursor)
        check(page == feed(USERS[0], **filters, cursor=cursor), "cursor replay returned different page")
    check(set(seen) == {("EVENT", item) for item in ids}, "cursor did not retain issued pool")
    check(("EVENT", fresh) in refs(feed(USERS[0], **filters)["items"]), "fresh pool omitted new publication")


def test_members(filters):
    room, token = lobby()
    room = start(room, filters)
    check(room["state"] == "VOTING" and len(roster(room)) == 4, "four participants did not start voting")
    check(room["round"]["memberCount"] == 4, "round member count")
    for user in USERS[:4]:
        seen = get(room, user)
        check(roster(seen) == roster(room) and cards(seen) == cards(room), "inconsistent room pool or roster")
    get(room, USERS[4], status=404, error="NOT_FOUND")
    try:
        join(token, USERS[4], status=409, error="INVALID_STATE")
    except AssertionError as failure:
        # The contract allows a private-room denial without prescribing this response code.
        if "received 404" not in str(failure):
            raise
    check(get(room, USERS[0]) == room, "late join changed the room")


def test_progress(filters):
    room = start(lobby()[0], filters)
    finish(room, USERS[0], status=409, error="INVALID_STATE")
    vote(room, USERS[0], cards(room)[0], "LIKE")
    fill(room, USERS[0])
    completed = finish(room, USERS[0])
    vote(room, USERS[0], cards(room)[0], "LIKE", status=409, error="INVALID_STATE")
    own = get(room, USERS[0])["round"]
    check(own == completed["round"] and own["myFinished"] and
          all(item["choice"] == "PASS" for item in own["myVotes"]), "own votes or completion not recovered")
    other = get(room, USERS[1])["round"]
    check(other["myVotes"] == [] and not other["myFinished"], "other participant received private progress")


def test_no_majority(filters, expected):
    room = start(lobby()[0], filters)
    for index, user in enumerate(USERS[:4]):
        fill(room, user, [0] if index < 2 else [])
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda user: finish(room, user), USERS[:4]))
    snapshot = get(room, USERS[0])
    check(snapshot["result"] is None, "two of four selected a winner")
    check(snapshot["state"] == expected, f"expected {expected} after no majority")
    if snapshot["state"] == "VOTING":
        check(snapshot["round"]["id"] != room["round"]["id"], "round did not advance")
        check(not set(cards(room)).intersection(cards(snapshot)), "next round reused shown cards")
        check(snapshot["round"]["finishedCount"] == 0, "new round inherited completion")
        for user in USERS[:4]:
            check(cards(get(room, user)) == cards(snapshot), "concurrent completion created divergent pools")
    else:
        check(snapshot["state"] == "EXHAUSTED" and snapshot["round"] is None, "invalid empty round state")
    for user in USERS[:4]:
        check(finish(room, user) == get(room, user), "completion replay returned a stale snapshot")
    vote(room, USERS[0], cards(room)[0], status=409, error="STALE_ROUND")
    return snapshot


def test_majority(filters):
    for tie in (True, False):
        room = start(lobby()[0], filters)
        for index, user in enumerate(USERS[:4]):
            liked = ([0] if index < 3 else []) + ([1] if not tie or index > 0 else [])
            fill(room, user, liked)
        for user in USERS[:2]:
            finish(room, user)
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda user: finish(room, user), USERS[2:4]))
        expected = cards(room)[0 if tie else 1]
        versions = set()
        for user in USERS[:4]:
            current = get(room, user)
            check(current["state"] == "MATCHED", "strict majority failed")
            winner = current["result"]["winner"]
            check((winner["kind"], winner["id"]) == expected, "wrong majority or pool-order winner")
            versions.add(current["version"])
        check(len(versions) == 1, "clients received different result versions")


def test_poll_join():
    room, token = lobby(1)
    with ThreadPoolExecutor(max_workers=1) as pool:
        wait = pending_poll(pool, room, USERS[0])
        joined = join(token, USERS[1])
        received = wait.result(timeout=5)
    check(received["version"] == joined["version"] > room["version"], "lobby poll version")
    check(USERS[1]["userId"] in roster(received), "lobby poll omitted joined participant")
    check(token not in json.dumps(received), "invite token present in room snapshot")
    return room, token


def test_poll_votes(filters):
    room = start(lobby(2)[0], filters)
    with ThreadPoolExecutor(max_workers=1) as pool:
        wait = pending_poll(pool, room, USERS[1])
        vote(room, USERS[0], cards(room)[0], "LIKE")
        received = wait.result(timeout=5)
    check(received["version"] > room["version"] and received["round"]["myVotes"] == [], "vote update or privacy")
    begin = time.monotonic()
    check(poll(room, USERS[1]) == received, "old version did not yield latest snapshot")
    check(time.monotonic() - begin < 2, "old version waited")
    fill(room, USERS[0])
    received = get(room, USERS[1])
    with ThreadPoolExecutor(max_workers=1) as pool:
        wait = pending_poll(pool, received, USERS[1])
        finish(room, USERS[0])
        snapshot = wait.result(timeout=5)
    check(snapshot["version"] > received["version"] and snapshot["round"]["finishedCount"] == 1,
          "completion did not wake poll")
    check(snapshot["round"]["myVotes"] == [] and not snapshot["round"]["myFinished"], "completion poll leaked votes")


def test_poll_timeout():
    room, token = lobby(1)
    begin = time.monotonic()
    poll(room, USERS[4], status=404, error="NOT_FOUND")
    check(time.monotonic() - begin < 2, "outsider poll did not return immediately")
    begin = time.monotonic()
    poll(room, USERS[0], status=204)
    elapsed = time.monotonic() - begin
    check(24 <= elapsed <= 32, f"default long wait took {elapsed:.2f}s")
    with ThreadPoolExecutor(max_workers=1) as pool:
        wait = pending_poll(pool, room, USERS[0])
        joined = join(token, USERS[1])
        check(wait.result(timeout=5)["version"] == joined["version"], "second poll did not recover")
    revoked = USERS[4]
    joined = join(token, revoked)
    with ThreadPoolExecutor(max_workers=1) as pool:
        wait = pending_poll(pool, joined, revoked, 3, status=401, error="SESSION_EXPIRED")
        request("DELETE", "/auth/session", revoked, status=204)
        wait.result(timeout=6)


def test_auth(unfinished):
    check(not unfinished["profileComplete"], "incomplete-profile fixture is already registered")
    for path in ["/feed/candidates?kind=EVENT", "/rooms/unknown"]:
        request("GET", path, status=401, error="UNAUTHENTICATED")
        request("GET", path, unfinished, status=403, error="PROFILE_INCOMPLETE")
    request("POST", "/rooms", body={}, status=401, error="UNAUTHENTICATED")
    request("POST", "/rooms", unfinished, {}, status=403, error="PROFILE_INCOMPLETE")


def health(status):
    return request("GET", "/swipes/health", status=status)


def test_health():
    database = os.getenv("MATCHING_TEST_DB", "swipes-db")
    health(200)
    compose("stop", database)
    try:
        body = health(503)
        check(all(value not in json.dumps(body).lower() for value in ("password", "postgresql://", "traceback")),
              "readiness included internal data")
    finally:
        compose("start", database)
    for _ in range(30):
        try:
            health(200)
            break
        except AssertionError:
            time.sleep(1)
    else:
        raise AssertionError("matching readiness failed to recover")
    logs = compose("logs", "--no-color", os.getenv("MATCHING_TEST_SERVICE", "swipes"))
    check("postgresql://" not in logs and "postgresql+asyncpg://" not in logs,
          "readiness failure logged a database connection URI")


def restart():
    compose("restart", os.getenv("MATCHING_TEST_SERVICE", "swipes"))
    for _ in range(30):
        try:
            health(200)
            return
        except AssertionError:
            time.sleep(1)
    raise AssertionError("matching did not recover from restart")


def test_restart(filters):
    room = test_no_majority(filters, "VOTING")
    check(room["state"] == "VOTING", "restart fixture needs a second round")
    fill(room, USERS[0], [0])
    finish(room, USERS[0])
    vote(room, USERS[1], cards(room)[0], "LIKE")
    prior = [get(room, user) for user in USERS[:4]]
    restart()
    check([get(room, user) for user in USERS[:4]] == prior, "snapshot changed after restart")
    for idx, user in enumerate(USERS[1:4]):
        fill(room, user, [0] if idx == 0 else [])
        finish(room, user)
    check(get(room, USERS[0])["state"] == "EXHAUSTED", "restart forgot cards used in earlier rounds")
    for _ in range(4):
        room, token = lobby(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            entering = pool.submit(join, token, USERS[2])
            started = pool.submit(start, room, filters).result()
            try:
                entering.result()
                joined = True
            except AssertionError as exc:
                if "received 409" not in str(exc) and "received 404" not in str(exc):
                    raise
                joined = False
        check(started["round"]["memberCount"] == len(roster(started)) == (3 if joined else 2),
              "start and join did not serialize")
        check(get(room, USERS[0]) == started, "room membership changed after start")
        if not joined:
            get(room, USERS[2], status=404, error="NOT_FOUND")


def test_cursor_expiry():
    global CLOCK
    places = {"kind": "PLACE", "categoryId": "dev-swipe-places"}
    try:
        CLOCK = "2089-01-01T00:00:00Z"
        first = feed(USERS[0], **places)
        check(first["nextCursor"], "controlled-clock fixture has no cursor")
        CLOCK = "2089-01-01T00:29:59Z"
        check(feed(USERS[0], **places, cursor=first["nextCursor"])["nextCursor"] is None,
              "cursor failed before its deadline")
        CLOCK = "2089-01-01T00:30:00Z"
        request("GET", f"/feed/candidates?{urlencode({**places, 'cursor': first['nextCursor']})}", USERS[0],
                status=409, error="CURSOR_EXPIRED")
    finally:
        CLOCK = None


def test_room_expiry():
    global CLOCK
    try:
        CLOCK = "2089-01-01T00:00:00Z"
        room = start(lobby()[0], {"kind": "PLACE", "categoryId": "dev-swipe-places"})
        vote(room, USERS[1], cards(room)[0], "LIKE")
        current = get(room, USERS[1])
        check(roster(current) == roster(room) and current["round"]["myVotes"], "reconnect lost membership or vote")
        restart()
        CLOCK = "2089-01-01T00:29:59Z"
        check(get(room, USERS[1]) == current, "restart altered room before its expiry")
        CLOCK = "2089-01-01T00:30:00Z"
        closed = get(room, USERS[1])
        check(closed["state"] == "CLOSED" and closed["round"] is None, "elapsed room did not close")
        check(roster(closed) == roster(room), "expiry changed roster")
        try:
            vote(room, USERS[1], cards(room)[0], status=409, error="STALE_ROUND")
        except AssertionError as exc:
            if "received INVALID_STATE" not in str(exc):
                raise
        check(get(room, USERS[1]) == closed, "vote changed a closed room")
    finally:
        CLOCK = None


def test_invite_expiry():
    global CLOCK
    try:
        CLOCK = "2089-01-01T00:00:00Z"
        room, token = lobby(1)
        CLOCK = "2089-01-01T00:29:59Z"
        join(token, USERS[1])
        CLOCK = "2089-01-01T00:30:00Z"
        join(token, USERS[2], status=410, error="INVITE_EXPIRED")
        check(USERS[2]["userId"] not in roster(get(room, USERS[0])), "expired invite changed roster")
    finally:
        CLOCK = None


def test_cancel(filters):
    import socket

    room, token = lobby(1)
    target = urlparse(BASE)
    with socket.create_connection((target.hostname, target.port), timeout=4) as connection:
        connection.sendall(
            (f"GET /v1/rooms/{room['id']}?afterVersion={room['version']}&waitSeconds=25 HTTP/1.1\r\n"
             f"Host: {target.netloc}\r\nAuthorization: Bearer {USERS[0]['accessToken']}\r\n\r\n").encode()
        )
        time.sleep(0.4)
    join(token, USERS[1])
    check(poll(room, USERS[0])["version"] > room["version"], "new poll failed after cancellation")
    logs = compose("logs", "--no-color")
    check(token not in logs, "invite token leaked to Compose logs")
    check(all(user["accessToken"] not in logs for user in USERS), "access token leaked to Compose logs")
    if filters:
        room = start(lobby(2)[0], filters)
        with ThreadPoolExecutor(max_workers=1) as pool:
            wait = pool.submit(poll, room, USERS[1], 4)
            vote(room, USERS[0], cards(room)[0])
            check(wait.result(timeout=6)["version"] > room["version"], "near-subscribe update was lost")


def test_compose(new_user):
    states = compose("ps", "--format", "json")
    try:
        entries = json.loads(states)
    except json.JSONDecodeError:
        entries = [json.loads(line) for line in states.splitlines()]
    expected = {"nginx", "identity", "catalog", "swipes", "swipes-db", "redis", "kafka"}
    check(expected <= {service["Service"] for service in entries}, "Compose omitted expected services")
    published = []
    for service in entries:
        check(service["State"] == "running", f"{service['Service']} is not running")
        check(service.get("Health") in (None, "", "healthy"), f"{service['Service']} is unhealthy")
        published.extend((service["Service"], port.get("URL")) for port in service.get("Publishers") or [] if port.get("PublishedPort"))
    check(published and all(name == "nginx" and host == "127.0.0.1" for name, host in published),
          "published ports include an unexpected service or interface")
    complete_registration(new_user)
    user = new_user
    prior = request("GET", "/catalog/categories", user)
    request("GET", "/events", user)
    compose("up", "--build", "-d", "--wait")
    categories = request("GET", "/catalog/categories", user)["items"]
    check(categories == prior["items"] and len({item["id"] for item in categories}) == len(categories),
          "restart duplicated or changed dev categories")
    check(request("GET", "/me", user)["profileComplete"], "registration did not survive repeat startup")
    get(lobby(2)[0], USERS[1])


def main():
    failed = 0
    requested = set(sys.argv[1:])

    def run(label, action):
        nonlocal failed
        if requested and label not in requested:
            print(f"SKIP {label}", flush=True)
            return None
        try:
            result = action()
        except Exception as exc:
            failed += 1
            # Print only assertion messages authored here. Network failures can embed URLs or request data.
            print(f"FAIL {label} {exc if isinstance(exc, AssertionError) else type(exc).__name__}", flush=True)
            return None
        print(f"PASS {label}", flush=True)
        return result

    try:
        USERS.extend(register(f"person{index}@example.test") for index in range(1, 6))
        new_user = register(os.getenv("MATCHING_TEST_NEW_EMAIL", "new@example.test"))
        filters, _ = fixture(3, [0, 1, None])
        wide, wide_ids = fixture(24)
    except Exception as exc:
        print(f"FAIL SETUP {exc if isinstance(exc, AssertionError) else type(exc).__name__}", flush=True)
        return 1
    run("AC-12", lambda: test_auth(new_user))
    run("AC-11", lambda: test_compose(new_user))
    run("AC-01", test_budget)
    run("AC-02", lambda: (test_pagination(wide, wide_ids), test_cursor_expiry()))
    run("AC-03", lambda: test_members(filters))
    run("AC-04", lambda: test_progress(filters))
    run("AC-05", lambda: (test_no_majority(wide, "VOTING"), test_no_majority(filters, "EXHAUSTED")))
    run("AC-06", lambda: test_majority(filters))
    run("AC-07", test_room_expiry)
    run("AC-08", test_poll_join)
    run("AC-09", lambda: test_poll_votes(filters))
    run("AC-10", test_poll_timeout)
    run("AC-13", test_health)
    run("AC-14", lambda: test_restart(wide))
    run("AC-15", lambda: (test_cancel(filters), test_invite_expiry()))
    return bool(failed)


if __name__ == "__main__":
    sys.exit(main())
