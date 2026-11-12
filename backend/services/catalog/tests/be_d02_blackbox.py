import concurrent.futures
import copy
import json
import os
import re
import subprocess
import uuid
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:18086"
PREFIX = "D02-" + uuid.uuid4().hex[:10]
NOW = "2091-01-01T00:00:00Z"
BASE_EVENT = {
    "description": "Acceptance fixture",
    "categoryId": "culture",
    "location": {"latitude": 43.11, "longitude": 131.89, "address": "Test address"},
    "startsAt": "2091-01-02T14:00:00Z",
    "timeZone": "Asia/Vladivostok",
    "admission": {"type": "REGISTRATION", "capacity": 1},
}
results = []


def check(name, test):
    try:
        test()
    except Exception as error:
        results.append(False)
        print(f"FAIL {name}: {error}")
    else:
        results.append(True)
        print(f"PASS {name}")


def http(method, path, token=None, body=None, status=200, code=None, key=None, now=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if method == "POST":
        headers["Idempotency-Key"] = key or uuid.uuid4().hex
    if now:
        headers["X-Dev-Catalog-Now"] = now
    data = json.dumps(body).encode() if body is not None else None
    try:
        response = urlopen(Request(BASE + path, data=data, headers=headers, method=method), timeout=20)
    except HTTPError as error:
        response = error
    raw = response.read()
    try:
        payload = json.loads(raw) if raw else {}
    except ValueError:
        payload = {}
    error_code = payload.get("error", {}).get("code")
    assert response.code in (status if isinstance(status, tuple) else (status,)), f"{method} {path} expected {status}, got {response.code} {error_code}"
    assert code is None or error_code == code, f"{method} {path} expected {code}, got {error_code}"
    return (response.code, payload) if isinstance(status, tuple) else payload


def login(destination, complete=True):
    challenge = http("POST", "/v1/auth/challenges", body={"channel": "EMAIL", "destination": destination}, status=201)
    session = http("POST", "/v1/auth/challenges/" + challenge["challengeId"] + "/verify", body={"code": "0427"})
    assert session["profileComplete"] is complete
    return session["accessToken"]


def event(label, **fields):
    return dict(copy.deepcopy(BASE_EVENT), title=PREFIX + "-" + label) | fields


def publish(body, **options):
    return http("POST", "/v1/events", owner, body, now=NOW, status=201, **options)


def read(path, token=None, **options):
    return http("GET", "/v1" + path, viewer if token is None else token, **options)


def ids(items):
    return [item["ref"]["id"] for item in items]


def pages(path, filters):
    items = []
    cursor = None
    while True:
        query = dict(filters, **({"cursor": cursor} if cursor else {}))
        page = read(path + "?" + urlencode(query), now=NOW)
        items.extend(page["items"])
        cursor = page["nextCursor"]
        if cursor is None:
            return items
        assert len(items) < 200, "pagination failed to terminate"


def compose(*args, env=None, timeout=40):
    return subprocess.run(["docker", "compose", "-p", "srastemsya-be-d02-tester",
                           "-f", "compose.yaml", "-f", "compose.dev.yaml", *args],
                          cwd="../../..", env=env, timeout=timeout, capture_output=True, text=True)


def visibility():
    global main_event
    body = event("main", coverMediaId="dev-event-cover-person1")
    key = uuid.uuid4().hex
    main_event = publish(body, key=key)
    assert publish(body, key=key) == main_event
    http("POST", "/v1/events", owner, dict(body, title=body["title"]+" changed"),
         now=NOW, key=key, status=409, code="IDEMPOTENCY_CONFLICT")
    assert main_event["cover"]["id"] == "dev-event-cover-person1"
    assert main_event["admission"] == admission(0)
    assert main_event["timeZone"] == "Asia/Vladivostok"
    assert main_event["endsAt"] == "2091-01-02T16:00:00Z"
    main_id = main_event["id"]
    assert ids(pages("/events", {"categoryId": "culture", "localDate": "2091-01-03"})).count(main_id) == 1
    assert ids(pages("/catalog/map", {"kind": "EVENT", "bbox": "131.89,43.11,131.89,43.11"})).count(main_id) == 1
    assert read("/events/" + main_id, now=NOW)["viewer"]["role"] == "VISITOR"
    assert read("/events/" + main_id) == read("/catalog/EVENT/" + main_id)
    http("GET", "/internal/catalog/candidates?kind=EVENT", viewer, status=404)
    source = """import json,os
from urllib.request import Request,urlopen
r=Request('http://catalog:8000/internal/catalog/candidates?kind=EVENT&categoryId=culture&localDate=2091-01-03',headers={'Authorization':'Bearer '+os.environ['ACCESS_TOKEN'],'X-Dev-Catalog-Now':'2091-01-01T00:00:00Z'})
print(urlopen(r).read().decode())
"""
    result = compose("exec", "-T", "-e", "ACCESS_TOKEN", "swipes", "python", "-c", source,
                     env=dict(os.environ, ACCESS_TOKEN=viewer))
    assert result.returncode == 0, "internal snapshot failed"
    assert ids(json.loads(result.stdout)["items"]).count(main_id) == 1


def admission(confirmed):
    return {"type": "REGISTRATION", "capacity": 1, "confirmedCount": confirmed, "remainingCount": 1-confirmed}


def validation():
    global open_event
    open_event = publish(event("paid-open", admission={"type": "OPEN"}, price={"amountMinor": 123, "currency": "RUB"}))
    assert open_event["admission"] == {"type": "OPEN"}
    assert open_event["price"] == {"amountMinor": 123, "currency": "RUB"}
    invalid = [
        ("open-cap", {"admission": {"type": "OPEN", "capacity": 1}}),
        ("no-cap", {"admission": {"type": "REGISTRATION"}}),
        ("zero-cap", {"admission": {"type": "REGISTRATION", "capacity": 0}}),
        ("fraction-cap", {"admission": {"type": "REGISTRATION", "capacity": 1.5}}),
        ("bool-cap", {"admission": {"type": "REGISTRATION", "capacity": True}}),
        ("paid", {"price": {"amountMinor": 1, "currency": "RUB"}}),
        ("latitude", {"location": dict(BASE_EVENT["location"], latitude=91)}),
        ("longitude", {"location": dict(BASE_EVENT["location"], longitude=181)}),
        ("address", {"location": dict(BASE_EVENT["location"], address="  ")}),
        ("category", {"categoryId": "unknown-acceptance-category"}),
        ("past", {"startsAt": NOW}),
        ("end", {"endsAt": BASE_EVENT["startsAt"]}),
        ("zone", {"timeZone": "UTC"}),
        ("foreign", {"coverMediaId": "dev-event-cover-person2"}),
        ("pending", {"coverMediaId": "dev-event-cover-pending"}),
        ("wrong-purpose", {"coverMediaId": "dev-event-cover-wrong-purpose"}),
    ]
    failures = []
    for label, mutation in invalid:
        try:
            error = http("POST", "/v1/events", owner, event(label, **mutation), now=NOW,
                         status=422, code="VALIDATION_ERROR")
            if label == "paid":
                assert error["error"]["details"]["fields"]["price"] == "PAID_REGISTRATION_UNSUPPORTED"
        except AssertionError as error:
            failures.append(f"{label}: {error}")
    for field in BASE_EVENT.keys() | {"title"}:
        body = event("missing-" + field)
        del body[field]
        try:
            http("POST", "/v1/events", owner, body, now=NOW, status=422, code="VALIDATION_ERROR")
        except AssertionError as error:
            failures.append(f"missing {field}: {error}")
    for field in ("title", "description"):
        body = event("blank-" + field)
        body[field] = "   "
        try:
            http("POST", "/v1/events", owner, body, now=NOW, status=422, code="VALIDATION_ERROR")
        except AssertionError as error:
            failures.append(f"blank {field}: {error}")
    actual = {item["title"] for item in pages("/events", {"localDate": "2091-01-03"}) if item["title"].startswith(PREFIX)}
    assert actual == {open_event["title"], main_event["title"]}, f"unexpected published fixtures: {actual}"
    assert not failures, "; ".join(failures)


def filters():
    before = publish(event("before-midnight", startsAt="2091-01-02T13:59:59Z"))
    assert before["id"] in ids(pages("/events", {"localDate": "2091-01-02"}))
    assert before["id"] not in ids(pages("/events", {"localDate": "2091-01-03"}))
    assert main_event["id"] not in ids(pages("/events", {"localDate": "2091-01-02"}))
    priced = ids(pages("/events", {"localDate": "2091-01-03", "maxPriceMinor": 123}))
    assert open_event["id"] in priced and main_event["id"] not in priced
    assert open_event["id"] not in ids(pages("/events", {"localDate": "2091-01-03", "maxPriceMinor": 122}))
    seats = ids(pages("/events", {"localDate": "2091-01-03", "onlyWithSeats": "true"}))
    assert main_event["id"] in seats and open_event["id"] not in seats
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(lambda n: publish(event(f"paging-{n}")), range(21)))
    query = {"localDate": "2091-01-03", "categoryId": "culture"}
    first = read("/events?" + urlencode(query), now=NOW)
    assert first["nextCursor"], "expected at least two pages"
    rows = pages("/events", query)
    assert len(ids(rows)) == len(set(ids(rows)))
    assert len([row for row in rows if row["title"].startswith(PREFIX)]) == 23
    ordered = [(item["startsAt"], item["ref"]["id"]) for item in rows]
    assert ordered == sorted(ordered)
    assert ids(rows) == ids(pages("/events", query))


def register(token, key=None, status=201, code=None, now=NOW):
    return http("POST", "/v1/events/" + main_event["id"] + "/registrations", token,
                key=key, status=status, code=code, now=now)


def concurrent_registration():
    global winner, reg_id
    key_by_token = {viewer: uuid.uuid4().hex, contender: uuid.uuid4().hex}

    def attempt(token):
        return register(token, key_by_token[token], status=(201, 409))

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        attempts = dict(zip((viewer, contender), pool.map(attempt, (viewer, contender))))
    assert sorted(status for status, _ in attempts.values()) == [201, 409]
    winner, original = next((token, result) for token, (status, result) in attempts.items() if status == 201)
    reg_id = original["registration"]["id"]
    full = next(result["error"] for status, result in attempts.values() if status == 409)
    assert full["code"] == "EVENT_FULL"
    assert all(full["details"][key] == value for key, value in admission(1).items() if key != "type")
    assert register(winner, key_by_token[winner]) == original
    assert register(winner, status=200) == original
    assert read("/events/" + main_event["id"], now=NOW)["admission"] == admission(1)
    assert main_event["id"] not in ids(pages("/events", {"localDate": "2091-01-03", "onlyWithSeats": "true"}))


def removal():
    path = "/events/" + main_event["id"] + "/registrations"
    read(path, contender, status=403, code="FORBIDDEN")
    active = read(path, owner)["items"]
    assert len(active) == 1 and active[0]["registration"]["id"] == reg_id
    assert active[0]["participant"]["id"] == active[0]["registration"]["userId"]
    assert active[0]["participant"]["displayName"]
    target = "/v1" + path + "/" + reg_id
    http("DELETE", target, contender, status=403, code="FORBIDDEN")
    removed = http("DELETE", target, owner, now=NOW)
    assert removed["admission"] == admission(0)
    assert removed["registration"]["status"] == "REMOVED"
    assert http("DELETE", target, owner, now=NOW) == removed
    assert read(path, owner)["items"] == []
    register(winner, status=409, code="REGISTRATION_REMOVED")
    assert read("/events/" + main_event["id"], now=NOW)["admission"] == admission(0)


def phases():
    path = "/events/" + main_event["id"]
    moments = [("2091-01-02T13:59:59.999999Z", "UPCOMING", True),
               ("2091-01-02T14:00:00Z", "ONGOING", False),
               ("2091-01-02T15:59:59.999999Z", "ONGOING", False),
               ("2091-01-02T16:00:00Z", "PAST", False)]
    unused = viewer if winner == contender else contender
    for moment, phase, can_register in moments:
        payload = read(path, unused, now=moment)
        assert (payload["phase"], payload["viewer"]["canRegister"]) == (phase, can_register), moment
    register(unused, status=409, code="EVENT_CLOSED", now=moments[1][0])


def regression():
    for service in ("identity", "catalog", "swipes"):
        http("GET", "/" + service + "/health")
    assert read("/me")["profileComplete"]
    home = read("/home")
    assert home["collections"][0]["id"] == "culture-events"
    assert home["quickCategories"]
    assert any(item["id"] == "culture" and "EVENT" in item["kinds"] for item in read("/catalog/categories")["items"])
    assert "dev-vlad-exhibit" in ids(read("/catalog/search?" + urlencode(home["collections"][0]["filters"]))["items"])
    assert "dev-vlad-museum" in ids(read("/catalog/map?kind=PLACE&bbox=131.87,43.10,131.91,43.13")["items"])
    assert read("/events/dev-vlad-workshop") == read("/catalog/EVENT/dev-vlad-workshop")
    assert read("/events/dev-vlad-workshop")["viewer"]["registration"]["status"] == "CONFIRMED"
    read("/events/dev-vlad-draft", status=404)
    read("/catalog/EVENT/dev-vlad-draft", status=404)
    assert home["collections"] == read("/home")["collections"]
    assert read("/catalog/search?kind=EVENT&q=" + uuid.uuid4().hex)["items"] == []
    cards = read("/catalog/search?" + urlencode(home["collections"][0]["filters"]))["items"]
    assert all(item["categoryId"] == "culture" and item["ref"]["kind"] == "EVENT" for item in cards)
    exhibit = next(item for item in cards if item["ref"]["id"] == "dev-vlad-exhibit")
    assert read("/events/dev-vlad-exhibit")["location"] == exhibit["location"]


def suggestions():
    for query in (None, "музей", None, "museum", "музей"):
        path = "/catalog/search/suggestions" + ("?" + urlencode({"q": query}) if query else "")
        status, body = read(path, status=(200, 422))
        error = body.get("error", {})
        fields = error.get("details", {}).get("fields", {})
        assert status == 200, f"{path} got {status} {error.get('code')} (fields: {fields})"
        assert isinstance(body["items"], list)


def security():
    paths = [("GET", "/v1/home"), ("GET", "/v1/catalog/map?kind=EVENT&bbox=131,43,132,44"),
             ("GET", "/v1/events"), ("POST", "/v1/events"),
             ("GET", "/v1/events/" + main_event["id"]),
             ("POST", "/v1/events/" + main_event["id"] + "/registrations"),
             ("GET", "/v1/events/" + main_event["id"] + "/registrations"),
             ("DELETE", "/v1/events/" + main_event["id"] + "/registrations/" + reg_id)]
    for method, path in paths:
        http(method, path, status=401)
        http(method, path, incomplete, status=403, code="PROFILE_INCOMPLETE")
    result = compose("ps", "--format", "json")
    assert result.returncode == 0, "compose ps failed"
    for line in result.stdout.splitlines():
        entry = json.loads(line)
        if entry["Service"] != "nginx":
            assert not any(port.get("PublishedPort", 0) for port in entry.get("Publishers") or []), entry["Service"]


def outage():
    stopped = compose("stop", "catalog-db")
    assert stopped.returncode == 0, "catalog-db stop failed"
    try:
        http("GET", "/catalog/health", status=503)
        error = read("/events", status=503)["error"]
        diagnostic = json.dumps(error).lower()
        assert not any(fragment in diagnostic for fragment in ("postgres", "password", "traceback", "bearer", "catalog-db"))
    finally:
        started = compose("up", "-d", "--wait", "catalog-db", timeout=80)
        assert started.returncode == 0, "catalog-db restore failed"
    http("GET", "/catalog/health")
    read("/events")
    logs = compose("logs", "--no-color", "catalog", "nginx")
    assert logs.returncode == 0, "catalog/nginx log access failed"
    assert not any(token in logs.stdout for token in (owner, viewer, contender, incomplete))
    assert not re.search(r"postgres(?:ql)?://[^\s]+:[^\s]+@|-----BEGIN (?:RSA )?PRIVATE KEY-----", logs.stdout)


def kafka():
    result = compose("exec", "-T", "kafka", "/opt/kafka/bin/kafka-console-consumer.sh",
                     "--bootstrap-server", "kafka:9092", "--topic", "catalog.changed.v1",
                     "--from-beginning", "--timeout-ms", "5000", "--property", "print.key=true")
    messages = []
    for line in result.stdout.splitlines():
        key, sep, body = line.partition("\t")
        if key == main_event["id"] and sep:
            messages.append(json.loads(body))
    unique = {msg["eventId"]: msg for msg in messages}
    assert len(unique) == 3, f"expected publication, booking, removal; got {len(unique)} distinct messages"
    revisions = []
    for msg in unique.values():
        assert set(msg) == {"eventId", "type", "kind", "objectId", "revision", "occurredAt"}
        assert (msg["type"], msg["kind"], msg["objectId"]) == ("CATALOG_OBJECT_CHANGED", "EVENT", main_event["id"])
        assert type(msg["revision"]) is int
        assert msg["occurredAt"].endswith(("Z", "+00:00"))
        revisions.append(msg["revision"])
    assert revisions == sorted(set(revisions))


def restart():
    result = compose("up", "--build", "-d", "--wait", env=dict(os.environ, NGINX_PORT="18086"), timeout=120)
    assert result.returncode == 0, "repeat documented startup failed"
    assert ids(pages("/events", {"localDate": "2091-01-03"})).count(main_event["id"]) == 1
    assert ids(pages("/catalog/search", {"kind": "EVENT"})).count("dev-vlad-exhibit") == 1
    read("/me")


def setup():
    global owner, viewer, contender, incomplete
    owner = login("person1@example.test")
    viewer = login("person2@example.test")
    contender = login("person3@example.test")
    incomplete = login("new@example.test", complete=False)


if __name__ == "__main__":
    checks = [
        ("AC-07 identity session fixtures", setup),
        ("AC-08 D01 regression and Nginx readiness", regression),
        ("Adjacent mobile contract: suggestions before repeat startup", suggestions),
        ("AC-01 publication, replay, map and internal snapshot", visibility),
        ("AC-02 publication validation, counters, cover and price", validation),
        ("AC-03 local midnight, price, seats and pagination", filters),
        ("AC-04 concurrent last seat and replay", concurrent_registration),
        ("AC-05 organizer permissions and repeated removal", removal),
        ("AC-06 phase boundaries and registration closure", phases),
        ("AC-07 Nginx access control and unpublished ports", security),
        ("AC-07 database outage and recovery", outage),
        ("AC-07 repeat documented startup and seed uniqueness", restart),
        ("AC-08 Kafka message key, DTO and mutation cardinality", kafka),
        ("Adjacent mobile contract: suggestions after repeat startup", suggestions),
    ]
    for label, test in checks:
        check(label, test)
    print(f"\nPassed: {sum(results)}\nFailed: {len(results)-sum(results)}\nSkipped: 0")
    raise SystemExit(not all(results))
