"""Black-box Discovery v1 release journey through the public Nginx listener."""

import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


ORIGIN = "http://127.0.0.1:18089"


def require(condition, description):
    if not condition:
        raise AssertionError(description)


def request(label, method, path, expected, token=None, body=None, query=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if method == "POST":
        headers["Idempotency-Key"] = uuid.uuid4().hex
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    if query:
        path += "?" + urlencode(query)
    started = time.monotonic()
    req = Request(ORIGIN + path, headers=headers, data=data, method=method)
    try:
        with urlopen(req, timeout=35) as response:
            status, raw = response.status, response.read()
    except HTTPError as response:
        with response:
            status, raw = response.code, response.read()
    print(f"- {label}: HTTP {status} ({time.monotonic() - started:.2f}s)")
    require(status in expected, f"{label} returned an unexpected HTTP status")
    return status, json.loads(raw) if raw else None


def call(label, method, path, expected, **kwargs):
    return request(label, method, "/v1" + path, (expected,), **kwargs)[1]


def sign_in(label, channel, destination, new=False):
    challenge = call(f"{label} challenge", "POST", "/auth/challenges", 201,
                     body={"channel": channel, "destination": destination})
    session = call(f"{label} verification", "POST",
                   f"/auth/challenges/{challenge['challengeId']}/verify", 200,
                   body={"code": "0427"})
    require(session["profileComplete"] is not new, f"{label} initial profile state")
    if new:
        profile = call(f"{label} registration", "PUT", "/me/registration", 200,
                       token=session["accessToken"],
                       body={"displayName": label, "birthDate": "1995-05-12"})
        require(profile["profileComplete"] and profile["id"] == session["userId"],
                f"{label} completed profile")
    return session["accessToken"], session["userId"]


def cards(label, path, token, query):
    items = []
    cursors = set()
    while True:
        page = call(label, "GET", path, 200, token=token, query=query)
        items.extend(page["items"])
        cursor = page["nextCursor"]
        if cursor is None:
            return items
        require(cursor not in cursors, f"{label} cursor repeated")
        cursors.add(cursor)
        query = {**query, "cursor": cursor}


def pending_poll(pool, label, room_path, version, owner):
    started = threading.Event()

    def poll():
        started.set()
        return call(label, "GET", room_path, 200, token=owner,
                    query={"afterVersion": version, "waitSeconds": 25})

    future = pool.submit(poll)
    require(started.wait(5), "poll worker started")
    time.sleep(0.75)
    require(not future.done(), f"{label} should remain pending before mutation")
    return future


def journey():
    for service in ("identity", "catalog", "swipes"):
        request(f"Nginx {service} health", "GET", f"/{service}/health", (200,))

    owner, owner_id = sign_in("Organizer", "EMAIL", "new@example.test", new=True)
    guest, guest_id = sign_in("Guest", "SMS", "+15550100100", new=True)
    rival, rival_id = sign_in("Second attendee", "EMAIL", "person3@example.test")
    require(len({owner_id, guest_id, rival_id}) == 3, "three distinct accounts")

    starts = (datetime.now(timezone.utc) + timedelta(days=2)).replace(microsecond=0)
    local_date = starts.astimezone(ZoneInfo("Asia/Vladivostok")).date().isoformat()
    category = "culture"
    title = "Release E2E final seat"
    filters = {"categoryId": category, "localDate": local_date}
    feed_filters = {**filters, "kind": "EVENT"}
    before = cards("Guest swipe before publication", "/feed/candidates", guest, feed_filters)

    event = call("Organizer publishes event", "POST", "/events", 201, token=owner,
                 body={"title": title, "description": "Release integration fixture",
                       "categoryId": category, "timeZone": "Asia/Vladivostok",
                       "startsAt": starts.isoformat().replace("+00:00", "Z"),
                       "location": {"latitude": 43.115, "longitude": 131.885,
                                    "address": "Release test venue"},
                       "price": {"amountMinor": 0, "currency": "RUB"},
                       "admission": {"type": "REGISTRATION", "capacity": 1}})
    ref = {"kind": "EVENT", "id": event["id"]}
    require(event["organizerId"] == owner_id, "publication belongs to organizer")
    require(all(card["ref"] != ref for card in before), "old swipe snapshot lacks new event")
    for label, path, params in (
        ("Guest event list", "/events", filters),
        ("Guest map", "/catalog/map", {**feed_filters, "bbox": "131.884,43.114,131.886,43.116"}),
        ("Guest fresh swipe", "/feed/candidates", feed_filters),
    ):
        matches = [card for card in cards(label, path, guest, params) if card["ref"] == ref]
        require(len(matches) == 1 and matches[0]["title"] == title,
                f"{label} exposes the same published event exactly once")

    event_path = f"/events/{ref['id']}"
    admission = {"type": "REGISTRATION", "capacity": 1, "confirmedCount": 1, "remainingCount": 0}
    with ThreadPoolExecutor(max_workers=2) as pool:
        barrier = threading.Barrier(2, timeout=5)

        def register(label, token):
            barrier.wait()
            return request(label, "POST", f"/v1{event_path}/registrations", (201, 409),
                           token=token)

        contenders = (("Guest claims seat", guest, guest_id),
                      ("Second attendee claims seat", rival, rival_id))
        attempts = [pool.submit(register, label, token) for label, token, _ in contenders]
        outcomes = [attempt.result() for attempt in attempts]

    require(sorted(status for status, _ in outcomes) == [201, 409],
            "one final-seat winner and one conflict")
    winner_id = contenders[0 if outcomes[0][0] == 201 else 1][2]
    for status, body in outcomes:
        if status == 201:
            require(body["registration"]["userId"] == winner_id
                    and body["registration"]["status"] == "CONFIRMED"
                    and body["admission"] == admission, "one confirmed final seat")
        else:
            require(body["error"]["code"] == "EVENT_FULL", "final-seat conflict code")
            require(all(body["error"]["details"].get(key) == admission[key]
                        for key in ("capacity", "confirmedCount", "remainingCount")),
                    "final-seat conflict has current counts")
    attendees = call("Organizer reads active registrations", "GET",
                     f"{event_path}/registrations", 200, token=owner)
    require([item["registration"]["userId"] for item in attendees["items"]] == [winner_id],
            "only the winning attendee appears in the roster")
    print("- Final-seat evidence: one CONFIRMED registration and EVENT_FULL with 1/1/0 counts")

    room = call("Organizer creates room", "POST", "/rooms", 201, token=owner, body={})
    room_path = f"/rooms/{room['id']}"
    invite = call("Organizer issues invite", "POST", f"{room_path}/invites", 201, token=owner)
    token = parse_qs(urlsplit(invite["url"]).query).get("token", [])
    require(len(token) == 1, "invite URL contains one join token")
    lobby = call("Organizer reads lobby", "GET", room_path, 200, token=owner)
    with ThreadPoolExecutor(max_workers=1) as pool:
        poll = pending_poll(pool, "Organizer lobby long poll", room_path, lobby["version"], owner)
        joined = call("Guest joins using invite URL token", "POST", "/room-invites/join", 200,
                      token=guest, body={"token": token[0]})
        updated = poll.result()
    require(joined["id"] == room["id"] and updated["state"] == "LOBBY"
            and updated["version"] > lobby["version"]
            and {member["userId"] for member in updated["members"]} == {owner_id, guest_id},
            "lobby long poll delivers the invited guest")

    room = call("Organizer starts event voting", "POST", f"{room_path}/start", 200,
                token=owner, body={"filters": {**feed_filters, "budgetTotal": None}})
    require(room["state"] == "VOTING", "room starts voting")
    round_path = f"{room_path}/rounds/{room['round']['id']}"
    candidates = [card["ref"] for card in room["round"]["candidates"]]
    require(ref in candidates, "published event appears in the room round")
    for label, account in (("Organizer", owner), ("Guest", guest)):
        for candidate in candidates:
            choice = "LIKE" if candidate == ref else "PASS"
            call(f"{label} votes {choice}", "PUT",
                 f"{round_path}/votes/{candidate['kind']}/{candidate['id']}", 200,
                 token=account, body={"choice": choice})
    owner_done = call("Organizer completes round", "PUT", f"{round_path}/completion",
                      200, token=owner)
    require(owner_done["state"] == "VOTING", "room waits for guest completion")
    with ThreadPoolExecutor(max_workers=1) as pool:
        poll = pending_poll(pool, "Organizer final-result long poll", room_path,
                            owner_done["version"], owner)
        call("Guest completes round", "PUT", f"{round_path}/completion", 200, token=guest)
        result = poll.result()
    require(result["id"] == room["id"] and result["version"] > owner_done["version"]
            and result["state"] == "MATCHED" and result["result"]["winner"] == ref,
            "Nginx long poll returns the published event as the terminal winner")
    print("- Room result: MATCHED with the same EVENT ref seen in list, map and new swipe pool")


if __name__ == "__main__":
    try:
        journey()
    except AssertionError as error:
        print(f"- FAIL: {error}")
        raise SystemExit(1)
    except Exception as error:
        print(f"- FAIL: scenario raised {type(error).__name__}")
        raise SystemExit(1)
