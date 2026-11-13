import concurrent.futures
import datetime as dt
import json
import pathlib
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

BASE = "http://127.0.0.1:18098"
T = "2089-01-01T00:00:00Z"
SWIPE = {"categoryId": "dev-swipe-events"}
TWO = {"categoryId": "dev-lobby-two"}
SHORT = {"categoryId": "dev-lobby-short"}
MIX = {"localDate": "2090-02-01"}
POOL = concurrent.futures.ThreadPoolExecutor(16)
ACTORS = []
NEW_USER = {}
CASES = []


def case(ids):
    def register(fn):
        CASES.append((ids.split(), fn))
        return fn
    return register


def request(method, path, user=None, body=None, status=200, error=None, now=None):
    headers = {}
    if user:
        headers["Authorization"] = "Bearer " + user["accessToken"]
    if method == "POST":
        headers["Idempotency-Key"] = str(uuid.uuid4())
    if body is not None:
        headers["Content-Type"] = "application/json"
    if now:
        headers["X-Dev-Swipes-Now"] = now
    data = json.dumps(body).encode() if body is not None else None
    try:
        result = urllib.request.urlopen(urllib.request.Request(BASE + path, data, headers, method=method), timeout=35)
    except urllib.error.HTTPError as exc:
        result = exc
    with result:
        raw = result.read()
        code = result.code
    if code != status:
        kind = None
        try:
            kind = json.loads(raw).get("error", {}).get("code")
        except (ValueError, AttributeError):
            pass
        raise AssertionError(f"{method} {path.split('?')[0]} expected HTTP {status}, got {code} ({kind})")
    if status == 204:
        assert raw == b""
    obj = json.loads(raw) if raw else None
    if error:
        assert obj["error"]["code"] == error, f"expected {error}, got {obj['error']['code']}"
    return obj


def api(method, path, *args, **kwargs):
    return request(method, "/v1" + path, *args, **kwargs)


def login(email):
    challenge = api("POST", "/auth/challenges", body={"channel": "EMAIL", "destination": email}, status=201)
    return api("POST", f"/auth/challenges/{challenge['challengeId']}/verify", body={"code": "0427"})


def register(user):
    assert not user["profileComplete"]
    assert api("PUT", "/me/registration", user, {"displayName": "Release QA", "birthDate": "1990-01-01"})["profileComplete"]


def room(users, now=None):
    state = api("POST", "/rooms", users[0], {"name": "BE-L07"}, status=201, now=now)
    url = api("POST", f"/rooms/{state['id']}/invites", users[0], status=201, now=now)["url"]
    token = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["token"][0]
    for user in users[1:]:
        join(user, token, now)
    return state, token


def join(user, token, now=None, **kwargs):
    return api("POST", "/room-invites/join", user, {"token": token}, now=now, **kwargs)


def start(state, user, filters, now=None):
    return api("POST", f"/rooms/{state['id']}/start", user,
               {"filters": {"kind": "EVENT", "budgetTotal": None, **filters}}, now=now)


def open_room(n, filters, now=None):
    users = ACTORS[:n]
    return start(room(users, now)[0], users[0], filters, now)


def get(state, user, now=None, **kwargs):
    return api("GET", f"/rooms/{state['id']}", user, now=now, **kwargs)


def poll(state, user, seconds=25, **kwargs):
    return api("GET", f"/rooms/{state['id']}?afterVersion={state['version']}&waitSeconds={seconds}", user, **kwargs)


def ids(state):
    return [c["ref"]["id"] for c in state["round"]["candidates"]]


def series(prefix, numbers):
    return [f"{prefix}-{i:02}" for i in numbers]


def vote(state, user, candidate, choice, **kwargs):
    return api("PUT", f"/rooms/{state['id']}/rounds/{state['round']['id']}/votes/EVENT/{candidate}",
               user, {"choice": choice}, **kwargs)


def complete(state, user, **kwargs):
    return api("PUT", f"/rooms/{state['id']}/rounds/{state['round']['id']}/completion", user, **kwargs)


def fill(state, users, scores, now=None):
    def participant(index, user):
        for candidate in ids(state):
            vote(state, user, candidate, "LIKE" if index < scores.get(candidate, 0) else "PASS", now=now)
    futures = [POOL.submit(participant, index, user) for index, user in enumerate(users)]
    for f in futures:
        f.result()


def settled(state, user, now=None):
    deadline = time.monotonic() + 12
    while True:
        snapshot = get(state, user, now)
        if snapshot["state"] != "REFRESHING":
            return snapshot
        assert time.monotonic() < deadline, "REFRESHING did not settle"
        time.sleep(.1)


def finish(state, users, now=None, concurrent=False):
    for user in users[:-2] if concurrent else users:
        complete(state, user, now=now)
    if concurrent:
        tasks = [POOL.submit(complete, state, u, now=now) for u in users[-2:]]
        for task in tasks:
            task.result()
    return settled(state, users[0], now)


def round_check(state, number, expected):
    assert state["state"] == "VOTING" and state["result"] is None
    assert state["round"]["number"] == number and ids(state) == expected, (number, ids(state), expected)


def terminal(state, expected):
    assert (state["state"], state["round"], state["result"]) == (expected, None, None)


def match(state, winner, basis, likes, members):
    assert state["state"] == "MATCHED", state["state"]
    assert state["result"] == {"winner": {"kind": "EVENT", "id": winner}, "basis": basis,
                               "likes": likes, "memberCount": members}, "unexpected public result"
    if basis == "TOP_SCORE":
        assert state["round"] is None
    else:
        assert state["round"]["finishedCount"] == members


def feed(user, **filters):
    return api("GET", "/feed/candidates?" + urllib.parse.urlencode({"kind": "EVENT", **filters}), user)


def event(user, category, date, registration=False):
    admission = {"type": "REGISTRATION", "capacity": 1} if registration else {"type": "OPEN"}
    return api("POST", "/events", user, {"title": "BE-L07 synthetic event", "description": "Release acceptance",
               "categoryId": category, "startsAt": date, "timeZone": "Asia/Vladivostok",
               "location": {"longitude": 131.89, "latitude": 43.11, "address": "Vladivostok"},
               "price": {"amountMinor": 0, "currency": "RUB"}, "admission": admission}, status=201)


def compose(*args):
    command = ["docker", "compose", "-p", "srastemsya_l07_test", "-f", "compose.yaml", "-f", "compose.dev.yaml", *args]
    return subprocess.run(command, check=True, text=True, capture_output=True, timeout=120).stdout


def ready(service):
    deadline = time.monotonic() + 60
    while True:
        try:
            request("GET", f"/{service}/health")
            return
        except (AssertionError, urllib.error.URLError):
            if time.monotonic() >= deadline:
                raise
            time.sleep(1)


@case("INT-01")
def authorization():
    incomplete = NEW_USER
    for path in ("/events", "/feed/candidates?kind=EVENT"):
        api("GET", path, status=401, error="UNAUTHENTICATED")
        api("GET", path, incomplete, status=403, error="PROFILE_INCOMPLETE")
    api("POST", "/rooms", body={}, status=401, error="UNAUTHENTICATED")
    api("POST", "/rooms", incomplete, {}, status=403, error="PROFILE_INCOMPLETE")


@case("L02-01 L02-02 L02-03 D03-03")
def progression():
    users = ACTORS[:4]
    before, token = room(users)
    state = start(before, users[0], SWIPE)
    for i, chunk in enumerate((range(1, 11), range(11, 21), range(21, 23)), 1):
        for user in users:
            observed = get(state, user)
            round_check(observed, i, series("dev-swipe-event", chunk))
            assert observed["members"] == state["members"]
            assert {x["userId"] for x in observed["members"]} == {x["userId"] for x in users}
        if i == 1:
            get(state, ACTORS[4], status=404, error="NOT_FOUND")
            join(ACTORS[4], token, status=409)
        fill(state, users, {})
        state = finish(state, users)
    terminal(state, "EXHAUSTED")
    first = feed(users[0], **SWIPE)
    assert len(first["items"]) == 20 and first["nextCursor"]


@case("L03-01 L03-02 L03-04")
def thresholds():
    for n, low, high in ((5, 3, 4), (2, 1, 2), (3, 2, 3), (10, 6, 7)):
        users = ACTORS[:n]
        state = open_room(n, TWO)
        assert state["result"] is None
        fill(state, users, {ids(state)[0]: low})
        state = finish(state, users)
        assert state["state"] == "VOTING" and state["round"]["number"] == 2
        assert state["result"] is None
        winner = ids(state)[0]
        fill(state, users, {winner: high})
        match(finish(state, users), winner, "THRESHOLD", high, n)


@case("L03-03")
def threshold_ties():
    users = ACTORS[:4]
    for equal in (True, False):
        state = open_room(4, SHORT)
        first, second = ids(state)[:2]
        fill(state, users, {first: 3, second: 3 if equal else 4})
        finish(state, users, concurrent=True)
        for user in users:
            match(get(state, user), first if equal else second, "THRESHOLD", 3 if equal else 4, 4)


@case("L04-01 L04-02 L04-03 L04-04")
def timing():
    users = ACTORS[:3]
    t20 = "2089-01-01T00:20:00Z"
    t30 = "2089-01-01T00:30:00Z"
    t50 = "2089-01-01T00:50:00Z"
    state = open_room(3, SWIPE, T)
    assert instant(state["round"]["expiresAt"]) == instant(t30)
    fill(state, users, {}, t20)
    state = finish(state, users, t20)
    assert instant(state["round"]["expiresAt"]) == instant(t50)
    round_check(get(state, users[0], t30), 2, series("dev-swipe-event", range(11, 21)))
    fill(state, users[:1], {}, t30)
    complete(state, users[0], now=t30)
    vote(state, users[1], ids(state)[0], "LIKE", now=t30)
    snapshots = [get(state, u, t30) for u in users]
    compose("restart", "swipes")
    ready("swipes")
    assert [get(state, u, t30) for u in users] == snapshots
    closed = get(state, users[0], t50)
    terminal(closed, "CLOSED")
    vote(state, users[1], ids(state)[0], "PASS", now=t50, status=409)
    complete(state, users[1], now=t50, status=409)
    assert get(state, users[0], t50) == closed


def instant(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


@case("L05-01 L05-02 L05-03 L05-05")
def weighted():
    users = ACTORS[:5]
    state = open_room(5, MIX)
    round_check(state, 1, series("dev-lobby-mix", range(1, 11)))
    fill(state, users, {x["ref"]["id"]: 3 for x in state["round"]["candidates"] if x["categoryId"] == "dev-lobby-a"})
    state = finish(state, users, concurrent=True)
    second = [11, 14, 17, 20, 23, 26, 29, 32, 35, 13]
    round_check(state, 2, series("dev-lobby-mix", second))
    snapshots = [get(state, u) for u in users]
    assert all(ids(s) == ids(state) and s["round"]["id"] == state["round"]["id"] for s in snapshots)
    compose("restart", "swipes")
    ready("swipes")
    assert [get(state, u) for u in users] == snapshots
    # Round two alone puts B (0) above C (-5). C remains above B (-25) cumulatively.
    fill(state, users, {x["ref"]["id"]: 3 for x in state["round"]["candidates"] if x["categoryId"] == "dev-lobby-a"})
    state = finish(state, users)
    round_check(state, 3, series("dev-lobby-mix", [16, 19, 22, 25, 28, 31, 34, 12, 15, 18]))


@case("L05-04")
def single_category():
    users = ACTORS[:5]
    state = open_room(5, TWO)
    round_check(state, 1, series("dev-lobby-two", range(1, 11)))
    fill(state, users, {})
    state = finish(state, users)
    round_check(state, 2, series("dev-lobby-two", range(11, 15)))


@case("L05-06")
def fresh_catalog_with_weights():
    users = ACTORS[:5]
    state = open_room(5, MIX)
    first = series("dev-lobby-mix", range(1, 11))
    round_check(state, 1, first)
    published = event(ACTORS[5], "dev-lobby-a", "2090-02-01T00:12:30Z")
    assert ids(get(state, users[0])) == first
    scores = {card["ref"]["id"]: 3 for card in state["round"]["candidates"]
              if card["categoryId"] == "dev-lobby-a"}
    fill(state, users, scores)
    state = finish(state, users)
    expected = series("dev-lobby-mix", [11]) + [published["id"]] + series(
        "dev-lobby-mix", [14, 17, 20, 23, 26, 29, 32, 35])
    for user in users:
        round_check(get(state, user), 2, expected)


@case("L06-01 L06-02")
def top_score():
    users = ACTORS[:3]
    for mode in ("unique", "across", "within"):
        state = open_room(3, TWO)
        winner, next_card = ids(state)[:2]
        fill(state, users, {winner: 2, next_card: 2 if mode == "within" else 0})
        state = finish(state, users)
        fill(state, users, {ids(state)[0]: 2 if mode == "across" else 1})
        match(finish(state, users), winner, "TOP_SCORE", 2, 3)



@case("L06-03 L06-04")
def terminal_variants():
    users = ACTORS[:2]
    state = open_room(2, SHORT)
    fill(state, users, {})
    terminal(finish(state, users), "EXHAUSTED")
    state = open_room(2, SHORT)
    winner = ids(state)[0]
    fill(state, users, {winner: 2})
    match(finish(state, users), winner, "THRESHOLD", 2, 2)
    empty = open_room(2, {**SWIPE, "budgetTotal": {"amountMinor": 0, "currency": "RUB"}})
    terminal(empty, "EXHAUSTED")


@case("L06-05")
def terminal_concurrent():
    users = ACTORS[:3]
    state = open_room(3, SHORT)
    winner = ids(state)[0]
    fill(state, users, {winner: 2})
    complete(state, users[0])
    current = get(state, users[0])
    pending = POOL.submit(poll, current, users[0])
    time.sleep(.35)
    assert not pending.done()
    for future in [POOL.submit(complete, state, u) for u in users[1:]]:
        future.result()
    update = pending.result()
    while update["state"] in ("VOTING", "REFRESHING"):
        update = poll(update, users[0])
    assert update["version"] > current["version"]
    match(update, winner, "TOP_SCORE", 2, 3)
    for user in users:
        observed = get(state, user)
        assert observed == update
        assert complete(state, user) == observed
    vote(state, users[0], winner, "PASS", status=409, error="STALE_ROUND")


@case("D03-04 D03-08 D03-09")
def progress_and_poll():
    users = ACTORS[:2]
    state, token = room(users[:1])
    future = POOL.submit(poll, state, users[0])
    time.sleep(.35)
    assert not future.done()
    joined = join(users[1], token)
    updated = future.result()
    assert updated["version"] > state["version"] and updated["members"] == joined["members"]
    assert token not in json.dumps(updated)
    state = start(state, users[0], SHORT)
    candidate = ids(state)[0]
    complete(state, users[1], status=409, error="INVALID_STATE")
    future = POOL.submit(poll, state, users[0])
    time.sleep(.35)
    assert not future.done()
    vote(state, users[1], candidate, "PASS")
    update = future.result()
    assert update["version"] > state["version"] and update["round"]["myVotes"] == []
    began = time.monotonic()
    assert poll(state, users[0]) == update and time.monotonic() - began < 3
    fill(state, users[1:], {candidate: 1})
    complete(state, users[1])
    reconnected = get(state, users[1])
    assert reconnected["round"]["myFinished"]
    assert next(v for v in reconnected["round"]["myVotes"] if v["candidate"]["id"] == candidate)["choice"] == "LIKE"
    assert get(state, users[0])["round"]["myVotes"] == []
    vote(state, users[1], candidate, "PASS", status=409)
    assert get(state, users[1]) == reconnected


@case("D03-10")
def timeout_and_revocation():
    user = NEW_USER
    state, _ = room([user])
    began = time.monotonic()
    poll(state, user, status=204)
    duration = time.monotonic() - began
    assert 24 <= duration < 33, f"poll took {duration:.2f}s"
    poll(state, user, 1, status=204)
    began = time.monotonic()
    poll(state, ACTORS[0], status=404, error="NOT_FOUND")
    assert time.monotonic() - began < 3
    future = POOL.submit(poll, state, user, 3, status=401, error="SESSION_EXPIRED")
    time.sleep(.4)
    assert not future.done()
    api("DELETE", "/auth/session", user, status=204)
    future.result()


@case("L07-02")
def release():
    organizer = NEW_USER
    register(organizer)
    users = [organizer, ACTORS[0], ACTORS[1]]
    published = event(organizer, "culture", "2091-06-13T00:05:00Z", True)
    path = f"/events/{published['id']}"
    assert api("GET", path, users[1])["admission"]["remainingCount"] == 1
    filters = {"localDate": "2091-06-13"}
    assert published["id"] in [x["ref"]["id"] for x in feed(users[1], **filters)["items"]]
    assert api("POST", path + "/registrations", users[1], status=201)["admission"]["remainingCount"] == 0
    api("POST", path + "/registrations", users[2], status=409, error="EVENT_FULL")
    state, token = room([organizer])
    join(users[1], token)
    state = start(state, organizer, filters)
    assert published["id"] in ids(state)
    fill(state, users[:2], {published["id"]: 2})
    complete(state, users[0])
    current = get(state, organizer)
    future = POOL.submit(poll, current, organizer)
    time.sleep(.35)
    assert not future.done()
    complete(state, users[1])
    update = future.result()
    assert update["version"] > current["version"]
    match(update, published["id"], "THRESHOLD", 2, 2)


@case("INT-00")
def startup_and_restart():
    services = ("identity", "catalog", "swipes")
    for service in services:
        ready(service)
    before_images = compose("images")
    print(before_images, flush=True)
    before = [feed(ACTORS[0], **f) for f in (SWIPE, TWO, SHORT)]
    compose("up", "--no-build", "-d", "--wait")
    assert compose("images") == before_images
    for service in services:
        ready(service)
    for original, filters in zip(before, (SWIPE, TWO, SHORT)):
        after = feed(ACTORS[0], **filters)
        assert after["items"] == original["items"]
    containers = [
        json.loads(line) for line in compose("ps", "--format", "json").splitlines()
    ]
    for container in containers:
        if container["Service"].endswith("-db") or container["Service"] in ("redis", "kafka"):
            assert not any(p.get("PublishedPort") for p in container["Publishers"] or [])
    assert api("GET", "/events", ACTORS[0])["items"]
    assert get(room(ACTORS[:1])[0], ACTORS[0])["state"] == "LOBBY"


@case("INT-02")
def database_failure():
    for service in ("identity", "catalog", "swipes"):
        db = service + "-db"
        try:
            compose("stop", db)
            response = request("GET", f"/{service}/health", status=503)
            assert not re.search(r"(password|postgresql?://|bearer )", json.dumps(response), re.I)
            logs = compose("logs", "--since", "20s", service)
            assert not re.search(r"(password\s*=|postgresql?://[^/ ]+:[^/ ]+@|bearer [A-Za-z0-9_.-]{20,})", logs, re.I)
        finally:
            compose("start", db)
            ready(service)


@case("L07-01")
def docs():
    root = pathlib.Path.cwd().parent
    docs_paths = ("docs/contracts/mobile-api.md", "docs/contracts/discovery-v1.md",
                  "docs/specs/backend.md", "docs/services/swipes.md", "backend/README.md")
    for relative in docs_paths:
        path = root / relative
        content = path.read_text()
        assert not re.search(r"строг.{0,9} большинств|от старта первого раунда|комнат.{0,20}до 20 карточ", content, re.I)
        assert "lobby-v2.md" in content
        for target in re.findall(r"\[[^\]\n]+\]\(([^)\s]+)\)", content):
            if "://" in target or target.startswith("mailto:"):
                continue
            file_part, _, fragment = target.partition("#")
            dest = path.parent / urllib.parse.unquote(file_part) if file_part else path
            assert dest.exists(), f"{relative}: missing link {target}"
            if not fragment or dest.suffix != ".md":
                continue
            headings = re.findall(r"^#+ (.+)$", dest.read_text(), re.M)
            slugs = [re.sub(r"[^\w-]", "", h.lower().replace(" ", "-")) for h in headings]
            assert urllib.parse.unquote(fragment) in slugs, f"{relative}: missing anchor {target}"
    discovery = (root / docs_paths[1]).read_text()
    single, shared = discovery.split("## Свайпы на одном устройстве")[1].split("## Свайпы в комнате")
    assert "20 элементов" in single
    for marker in ("70%", "TOP_SCORE", "THRESHOLD", "до 10 карточек", "30 минут с момента своего создания", "лайки − пропуски"):
        assert marker in shared


if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(10) as workers:
        ACTORS.extend(workers.map(login, [f"person{i}@example.test" for i in range(1, 11)]))
    assert all(user["profileComplete"] for user in ACTORS)
    NEW_USER.update(login("new@example.test"))
    failed = 0
    order = {"L07-01": 0, "INT-00": 1, "INT-01": 2, "L07-02": 3, "L05-04": 100, "L05-06": 101, "INT-02": 102}
    for keys, fn in sorted(CASES, key=lambda entry: order.get(entry[0][0], 10)):
        try:
            fn()
        except Exception as exc:
            print(f"FAIL {' '.join(keys)} · {type(exc).__name__}: {exc}", flush=True)
            failed += 1
        else:
            print(f"PASS {' '.join(keys)}", flush=True)
    raise SystemExit(bool(failed))
