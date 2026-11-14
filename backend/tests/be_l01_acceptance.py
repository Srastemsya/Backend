#!/usr/bin/env python3
"""BE-L01 black-box acceptance through Nginx (public HTTP API only).

Verifies AC-01..AC-08 of reports/BE-L01/acceptance.md against an isolated
Compose stand. Does not read application sources or internal state: only the
published HTTP contract, dev data and Docker Compose process metadata
(published ports) are used.

Environment:
  BE_L01_BASE_URL           base URL via Nginx (default http://127.0.0.1:18090)
  BE_L01_PREV_IDS           JSON from be_l01_prev_capture.py (users 1-5)
  BE_L01_COMPOSE_PROJECT    Compose project for the published-port check
  BE_L01_README             README path (default ../README.md)
"""
import datetime
import json
import os
import re
import subprocess
import sys
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
import uuid

OTP = "0427"
BASE = os.environ.get("BE_L01_BASE_URL", "http://127.0.0.1:18090").rstrip("/")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
README = os.environ.get("BE_L01_README", os.path.join(REPO, "backend", "README.md"))
PREV_IDS_PATH = os.environ.get("BE_L01_PREV_IDS", "")
COMPOSE_PROJECT = os.environ.get("BE_L01_COMPOSE_PROJECT", "")

MIX_CATEGORY = {}
for n in range(1, 36):
    if n <= 10:
        MIX_CATEGORY[n] = "dev-lobby-a" if n % 2 else "dev-lobby-b"
    elif n % 3 == 2:
        MIX_CATEGORY[n] = "dev-lobby-a"
    elif n % 3 == 0:
        MIX_CATEGORY[n] = "dev-lobby-b"
    else:
        MIX_CATEGORY[n] = "dev-lobby-c"


def api(path, method="GET", body=None, token=None, headers=None):
    data = None
    h = {"Content-Type": "application/json"}
    if method in ("POST", "PUT", "DELETE"):
        h["Idempotency-Key"] = str(uuid.uuid4())
    if headers:
        h.update(headers)
    if body is not None:
        data = json.dumps(body).encode()
    if token:
        h["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            payload = json.loads(raw) if raw else None
        except ValueError:
            payload = {"raw": raw[:200].decode("utf-8", "replace")}
        return exc.code, payload, dict(exc.headers)


def login(email, channel="EMAIL"):
    deadline = time.time() + 180
    while True:
        status, payload, headers = api(
            "/v1/auth/challenges", "POST",
            {"channel": channel, "destination": email},
        )
        if status == 429:
            if time.time() > deadline:
                raise AssertionError("challenge rate limited for %s" % email)
            try:
                delay = float(headers.get("Retry-After", "61"))
            except ValueError:
                delay = 61.0
            time.sleep(max(1.0, min(delay, deadline - time.time())))
            continue
        if status != 201:
            raise AssertionError("challenge %s -> %s %s" % (email, status, payload))
        break
    status, session, _ = api(
        "/v1/auth/challenges/%s/verify" % payload["challengeId"], "POST",
        {"code": OTP},
    )
    if status != 200:
        raise AssertionError("verify %s -> %s %s" % (email, status, session))
    return session


def parse_ts(value):
    text = value.replace("Z", "+00:00")
    parsed = datetime.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed.astimezone(datetime.timezone.utc)


def read_all(token, query, headers=None):
    items, cursor, pages, cursors = [], None, 0, set()
    while True:
        path = "/v1/feed/candidates?" + query
        if cursor:
            path += "&cursor=" + urllib.parse.quote(cursor, safe="")
        status, payload, _ = api(path, token=token, headers=headers)
        if status != 200:
            raise AssertionError("%s -> %s %s" % (path, status, payload))
        items.extend(payload["items"])
        pages += 1
        cursor = payload.get("nextCursor")
        if not cursor:
            return items, pages
        if cursor in cursors:
            raise AssertionError("cursor repeated: %s" % cursor)
        cursors.add(cursor)
        if pages > 20:
            raise AssertionError("too many pages for %s" % query)


def ids(items):
    return [item["ref"]["id"] for item in items]


def slugify(text):
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"\s", "-", text)
    return text


def wait_stable(token, room_id, attempts=10):
    last = None
    for _ in range(attempts):
        status, room, _ = api("/v1/rooms/" + room_id, token=token)
        if status != 200:
            raise AssertionError("GET room -> %s %s" % (status, room))
        last = room
        if room["state"] != "REFRESHING":
            return room
        time.sleep(0.3)
    return last


class L01(unittest.TestCase):
    sessions = {}
    prev = {}
    phone_session = None

    @classmethod
    def setUpClass(cls):
        if PREV_IDS_PATH and os.path.exists(PREV_IDS_PATH):
            with open(PREV_IDS_PATH, encoding="utf-8") as handle:
                cls.prev = json.load(handle)
        for number in range(1, 11):
            email = "person%d@example.test" % number
            cls.sessions[email] = login(email)
        cls.phone_session = login("+15550100100", channel="SMS")

    def token(self, number):
        return self.sessions["person%d@example.test" % number]["accessToken"]

    def get(self, path, token, headers=None):
        status, payload, _ = api(path, token=token, headers=headers)
        self.assertEqual(status, 200, "%s -> %s %s" % (path, status, payload))
        return payload

    def create_room(self, token, name="L01"):
        status, payload, _ = api("/v1/rooms", "POST", {"name": name}, token=token)
        self.assertEqual(status, 201, "POST /rooms -> %s %s" % (status, payload))
        return payload

    def invite(self, token, room_id, headers=None):
        status, payload, _ = api(
            "/v1/rooms/%s/invites" % room_id, "POST", {}, token=token, headers=headers
        )
        self.assertEqual(status, 201, "invite -> %s %s" % (status, payload))
        token_value = urllib.parse.parse_qs(
            urllib.parse.urlparse(payload["url"]).query
        )["token"][0]
        return token_value

    def join(self, token, invite_token, headers=None):
        status, payload, _ = api(
            "/v1/room-invites/join", "POST", {"token": invite_token},
            token=token, headers=headers,
        )
        self.assertEqual(status, 200, "join -> %s %s" % (status, payload))
        return payload

    def test_ac01_login_participants_and_stable_ids(self):
        for number in range(6, 11):
            email = "person%d@example.test" % number
            session = self.sessions[email]
            self.assertTrue(session["profileComplete"], email)
            profile = self.get("/v1/me", session["accessToken"])
            self.assertEqual(profile["id"], session["userId"])
            self.assertTrue(profile["profileComplete"], email)
            home = self.get("/v1/home", session["accessToken"])
            self.assertIsInstance(home["collections"], list)
            feed = self.get(
                "/v1/feed/candidates?kind=EVENT&categoryId=dev-swipe-events",
                session["accessToken"],
            )
            self.assertTrue(feed["items"], email)
            room = self.create_room(session["accessToken"], "AC-01 " + email)
            self.assertEqual(room["state"], "LOBBY")

        self.assertTrue(self.prev, "previous-build user ids are required for AC-01")
        for number in range(1, 6):
            email = "person%d@example.test" % number
            expected = self.prev[email]
            session = self.sessions[email]
            self.assertEqual(session["userId"], expected["userId"], email)
            profile = self.get("/v1/me", session["accessToken"])
            self.assertEqual(profile["id"], expected["profileId"], email)
            self.assertTrue(profile["profileComplete"], email)

    def test_ac02_mixed_set(self):
        token = self.token(6)
        items, pages = read_all(token, "kind=EVENT&localDate=2090-02-01")
        self.assertEqual(pages, 2, "35 cards are served in two pages of 20")
        expected_ids = ["dev-lobby-mix-%02d" % n for n in range(1, 36)]
        self.assertEqual(ids(items), expected_ids)
        self.assertEqual(len(set(ids(items))), 35, "duplicate cards in the set")
        base = datetime.datetime(2090, 2, 1, tzinfo=datetime.timezone.utc)
        for number, item in enumerate(items, start=1):
            self.assertEqual(item["ref"]["kind"], "EVENT")
            self.assertEqual(
                parse_ts(item["startsAt"]),
                base + datetime.timedelta(minutes=number),
                item["ref"]["id"],
            )
            self.assertEqual(item["price"]["amountMinor"], 1000, item["ref"]["id"])
            self.assertEqual(item["categoryId"], MIX_CATEGORY[number], item["ref"]["id"])

    def test_ac03_short_and_two_sets(self):
        token = self.token(6)
        for category, count, day in (
            ("dev-lobby-short", 4, 1),
            ("dev-lobby-two", 14, 2),
        ):
            items, _ = read_all(token, "kind=EVENT&categoryId=" + category)
            prefix = category.replace("dev-lobby-", "dev-lobby-")
            expected_ids = ["%s-%02d" % (prefix, n) for n in range(1, count + 1)]
            self.assertEqual(ids(items), expected_ids, category)
            self.assertEqual(len(set(ids(items))), count, category)
            base = datetime.datetime(2090, 3, day, tzinfo=datetime.timezone.utc)
            for number, item in enumerate(items, start=1):
                self.assertEqual(item["categoryId"], category, item["ref"]["id"])
                self.assertEqual(
                    parse_ts(item["startsAt"]),
                    base + datetime.timedelta(minutes=number),
                    item["ref"]["id"],
                )
                self.assertEqual(item["price"]["amountMinor"], 1000, item["ref"]["id"])

    def test_ac04_idempotent_restart_and_int00(self):
        # The run script repeats the documented Compose command on the same
        # volumes before this suite: counts must not double.
        token = self.token(6)
        for path in ("/identity/health", "/catalog/health", "/swipes/health"):
            status, payload, _ = api(path)
            self.assertEqual(status, 200, "%s -> %s %s" % (path, status, payload))

        mix, _ = read_all(token, "kind=EVENT&localDate=2090-02-01")
        short, _ = read_all(token, "kind=EVENT&categoryId=dev-lobby-short")
        two, _ = read_all(token, "kind=EVENT&categoryId=dev-lobby-two")
        events, _ = read_all(token, "kind=EVENT&categoryId=dev-swipe-events")
        places, _ = read_all(token, "kind=PLACE&categoryId=dev-swipe-places")
        self.assertEqual(len(mix), 35, "mixed set duplicated after restart")
        self.assertEqual(len(short), 4, "short set duplicated after restart")
        self.assertEqual(len(two), 14, "two-round set duplicated after restart")
        self.assertEqual(len(events), 22, "dev-swipe-events changed or duplicated")
        self.assertEqual(len(places), 22, "dev-swipe-places changed or duplicated")
        for name, items in (("mix", mix), ("short", short), ("two", two),
                            ("events", events), ("places", places)):
            self.assertEqual(len(set(ids(items))), len(items), name + " has duplicates")

        # Registration remains reachable through Nginx (profile is completed in AC-06).
        status, profile, _ = api(
            "/v1/me", token=self.phone_session["accessToken"]
        )
        self.assertEqual(status, 200)
        self.assertIn("profileComplete", profile)
        self.assertEqual(profile["id"], self.phone_session["userId"])

        afisha = self.get("/v1/events", token)
        self.assertIn("items", afisha)
        self.assertTrue(afisha["items"])
        room = self.create_room(self.token(1), "AC-04 rooms available")
        self.assertEqual(room["state"], "LOBBY")

        if COMPOSE_PROJECT:
            names_out = subprocess.run(
                ["docker", "ps", "--filter",
                 "label=com.docker.compose.project=" + COMPOSE_PROJECT,
                 "--format", "{{.Names}}"],
                check=True, capture_output=True, text=True,
            ).stdout
            names = [line.strip() for line in names_out.splitlines() if line.strip()]
            self.assertTrue(names, "no containers for project " + COMPOSE_PROJECT)
            for name in names:
                if name.endswith(("-identity-db-1", "-catalog-db-1", "-swipes-db-1",
                                  "-redis-1", "-kafka-1")):
                    out = subprocess.run(
                        ["docker", "inspect", "--format",
                         "{{json .HostConfig.PortBindings}}", name],
                        check=True, capture_output=True, text=True,
                    ).stdout.strip()
                    self.assertIn(out, ("{}", "null"), "%s publishes ports: %s" % (name, out))
            nginx = [n for n in names if n.endswith("-nginx-1")]
            self.assertEqual(len(nginx), 1)
            out = subprocess.run(
                ["docker", "inspect", "--format",
                 "{{json .HostConfig.PortBindings}}", nginx[0]],
                check=True, capture_output=True, text=True,
            ).stdout
            bindings = json.loads(out)
            for entries in bindings.values():
                for entry in entries:
                    self.assertEqual(entry.get("HostIp"), "127.0.0.1",
                                     "Nginx published outside loopback: %s" % out)

    def test_ac05_readme_documents_sets_and_links(self):
        self.assertTrue(os.path.exists(README), README)
        with open(README, encoding="utf-8") as handle:
            text = handle.read()
        start = text.find("## Стендовые данные комнаты BE-L01")
        self.assertGreaterEqual(start, 0, "README misses the BE-L01 section")
        end = text.find("\n## ", start + 1)
        section = text[start:] if end < 0 else text[start:end]
        for marker in ("person6", "person10"):
            self.assertIn(marker, section, "BE-L01 section misses " + marker)
        self.assertIn("new@example.test", text)
        self.assertIn("dev-lobby-mix-01", section)
        self.assertIn("dev-lobby-mix-35", section)
        self.assertIn("dev-lobby-short-01", section)
        self.assertIn("dev-lobby-short-04", section)
        self.assertIn("dev-lobby-two-01", section)
        self.assertIn("dev-lobby-two-14", section)
        for literal in (
            "1 февраля 2090", "1 марта 2090", "2 марта 2090",
            "dev-lobby-a", "dev-lobby-b", "dev-lobby-c",
            "dev-lobby-short", "dev-lobby-two",
            "kind=EVENT&localDate=2090-02-01",
            "kind=EVENT&categoryId=dev-lobby-short",
            "kind=EVENT&categoryId=dev-lobby-two",
        ):
            self.assertIn(literal, section, "BE-L01 section misses " + literal)

        base_dir = os.path.dirname(README)
        failures = []
        for label, target in re.findall(r"\[([^\]]*)\]\(([^)]+)\)", text):
            if target.startswith(("http://", "https://", "mailto:", "tel:", "#")):
                continue
            path, _, anchor = target.partition("#")
            resolved = os.path.normpath(os.path.join(base_dir, path))
            if not os.path.exists(resolved):
                failures.append("%s -> %s" % (label, target))
                continue
            if anchor and resolved.endswith(".md"):
                with open(resolved, encoding="utf-8") as handle:
                    headings = [
                        slugify(m.group(1))
                        for m in re.finditer(r"(?m)^#{1,6}\s+(.*)$", handle.read())
                    ]
                if urllib.parse.unquote(anchor) not in headings:
                    failures.append("%s -> %s (anchor)" % (label, target))
        self.assertEqual(failures, [], "broken README links: %s" % failures)

    def test_ac06_public_api_unchanged(self):
        status, payload, _ = api("/v1/feed/candidates?kind=EVENT")
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"]["code"], "UNAUTHENTICATED")

        status, payload, _ = api(
            "/v1/feed/candidates?kind=EVENT",
            token=self.phone_session["accessToken"],
        )
        # A fresh stand has the documented phone contact without a completed
        # profile: the first request must be rejected with PROFILE_INCOMPLETE.
        # On a reused stand the scenario is still asserted through /me.
        incomplete = None
        if not self.phone_session["profileComplete"]:
            incomplete = self.phone_session
            self.assertEqual(status, 403)
            self.assertEqual(payload["error"]["code"], "PROFILE_INCOMPLETE")
        else:
            self.assertEqual(status, 200, payload)

        token = self.token(6)
        first = self.get(
            "/v1/feed/candidates?kind=EVENT&categoryId=dev-swipe-events", token
        )
        self.assertEqual(len(first["items"]), 20)
        self.assertTrue(first["nextCursor"])
        repeat = self.get(
            "/v1/feed/candidates?kind=EVENT&categoryId=dev-swipe-events&cursor="
            + urllib.parse.quote(first["nextCursor"], safe=""),
            token,
        )
        again = self.get(
            "/v1/feed/candidates?kind=EVENT&categoryId=dev-swipe-events&cursor="
            + urllib.parse.quote(first["nextCursor"], safe=""),
            token,
        )
        self.assertEqual(ids(repeat["items"]), ids(again["items"]),
                         "cursor repeat returns a different page")
        self.assertEqual(len(repeat["items"]), 2)
        self.assertIsNone(repeat["nextCursor"])
        self.assertFalse(set(ids(first["items"])) & set(ids(repeat["items"])))

        old = {"X-Dev-Swipes-Now": "2089-01-01T00:00:00Z"}
        status, created, _ = api(
            "/v1/feed/candidates?kind=EVENT&categoryId=dev-swipe-events",
            token=token, headers=old,
        )
        self.assertEqual(status, 200)
        self.assertTrue(created["nextCursor"])
        expired = {"X-Dev-Swipes-Now": "2089-01-01T00:31:00Z"}
        status, payload, _ = api(
            "/v1/feed/candidates?kind=EVENT&categoryId=dev-swipe-events&cursor="
            + urllib.parse.quote(created["nextCursor"], safe=""),
            token=token, headers=expired,
        )
        self.assertEqual(status, 409, payload)
        self.assertEqual(payload["error"]["code"], "CURSOR_EXPIRED")

        key = str(uuid.uuid4())
        status, room1, _ = api(
            "/v1/rooms", "POST", {"name": "idem"}, token=token,
            headers={"Idempotency-Key": key},
        )
        self.assertEqual(status, 201)
        status, room2, _ = api(
            "/v1/rooms", "POST", {"name": "idem"}, token=token,
            headers={"Idempotency-Key": key},
        )
        self.assertIn(status, (200, 201))
        self.assertEqual(room1["id"], room2["id"])
        status, payload, _ = api(
            "/v1/rooms", "POST", {"name": "different"}, token=token,
            headers={"Idempotency-Key": key},
        )
        self.assertEqual(status, 409)
        self.assertEqual(payload["error"]["code"], "IDEMPOTENCY_CONFLICT")

        room = self.create_room(token, "invite expiry")
        invite_token = self.invite(token, room["id"], old)
        status, payload, _ = api(
            "/v1/room-invites/join", "POST", {"token": invite_token},
            token=self.token(9), headers=expired,
        )
        self.assertEqual(status, 410, payload)
        self.assertEqual(payload["error"]["code"], "INVITE_EXPIRED")

        room = self.create_room(token, "long poll")
        invite_token = self.invite(token, room["id"])
        version = room["version"]
        box = {}

        def poll():
            box["result"] = api(
                "/v1/rooms/%s?afterVersion=%s&waitSeconds=20" % (room["id"], version),
                token=token,
            )

        thread = threading.Thread(target=poll)
        thread.start()
        time.sleep(0.7)
        joined = self.join(self.token(2), invite_token)
        thread.join(timeout=30)
        self.assertFalse(thread.is_alive(), "long poll did not return")
        status, payload, _ = box["result"]
        self.assertEqual(status, 200, "long poll -> %s %s" % (status, payload))
        self.assertGreater(payload["version"], version)
        self.assertIn(self.sessions["person2@example.test"]["userId"],
                      [m["userId"] for m in payload["members"]])
        self.assertNotIn(invite_token, json.dumps(payload))
        self.assertEqual(joined["id"], room["id"])

        if incomplete is not None:
            status, profile, _ = api(
                "/v1/me/registration", "PUT",
                {"displayName": "Новый участник", "birthDate": "1990-01-01"},
                token=incomplete["accessToken"],
            )
            self.assertEqual(status, 200, profile)
            self.assertTrue(profile["profileComplete"])
            feed = self.get("/v1/feed/candidates?kind=EVENT",
                            incomplete["accessToken"])
            self.assertTrue(feed["items"])
        else:
            profile = self.get("/v1/me", self.phone_session["accessToken"])
            self.assertTrue(profile["profileComplete"])

    def test_ac07_existing_dev_data_and_single_room_pass(self):
        token = self.token(6)
        events, _ = read_all(token, "kind=EVENT&categoryId=dev-swipe-events")
        places, _ = read_all(token, "kind=PLACE&categoryId=dev-swipe-places")
        self.assertEqual(ids(events), ["dev-swipe-event-%02d" % n for n in range(1, 23)])
        self.assertEqual(ids(places), ["dev-swipe-place-%02d" % n for n in range(1, 23)])
        base = datetime.datetime(2090, 1, 2, tzinfo=datetime.timezone.utc)
        for number, card in enumerate(events, start=1):
            self.assertEqual(parse_ts(card["startsAt"]),
                             base + datetime.timedelta(minutes=number))
            expected = 500 if number == 21 else (None if number == 22 else 1000)
            self.assertEqual(card["price"]["amountMinor"] if card["price"] else None,
                             expected, card["ref"]["id"])
        for number, card in enumerate(places, start=1):
            expected = 500 if number == 21 else (None if number == 22 else 1000)
            self.assertEqual(card["price"]["amountMinor"] if card["price"] else None,
                             expected, card["ref"]["id"])

        for kind, ident in (
            ("EVENT", "dev-vlad-exhibit"),
            ("EVENT", "dev-vlad-workshop"),
            ("PLACE", "dev-vlad-museum"),
            ("ACTIVITY", "dev-vlad-walk"),
        ):
            status, payload, _ = api("/v1/catalog/%s/%s" % (kind, ident), token=token)
            self.assertEqual(status, 200, "%s %s -> %s" % (kind, ident, status))
            self.assertEqual(payload.get("id", (payload.get("card") or {}).get("ref", {}).get("id")),
                             ident)
        for kind in ("EVENT", "PLACE", "ACTIVITY"):
            status, _, _ = api("/v1/catalog/%s/dev-vlad-draft" % kind, token=self.token(2))
            self.assertEqual(status, 404, "draft visible to another user as " + kind)

        room = self.create_room(self.token(1), "single pass")
        invite_tokens = []
        for number in (2, 3, 4):
            invite_tokens.append(self.invite(self.token(1), room["id"]))
        for number, invite_token in zip((2, 3, 4), invite_tokens):
            self.join(self.token(number), invite_token)
        status, started, _ = api(
            "/v1/rooms/%s/start" % room["id"], "POST",
            {"filters": {"kind": "EVENT", "categoryId": "dev-swipe-events",
                         "budgetTotal": None}},
            token=self.token(1),
        )
        self.assertEqual(status, 200, started)
        self.assertEqual(started["state"], "VOTING")
        round1 = started["round"]
        self.assertEqual(round1["memberCount"], 4)
        self.assertEqual(ids(round1["candidates"]),
                         ["dev-swipe-event-%02d" % n for n in range(1, 21)])
        other_view = self.get("/v1/rooms/" + room["id"], self.token(2))
        self.assertEqual(ids(other_view["round"]["candidates"]),
                         ids(round1["candidates"]))
        self.assertEqual([m["userId"] for m in started["members"]],
                         [m["userId"] for m in other_view["members"]])

        first = round1["candidates"][0]["ref"]
        status, payload, _ = api(
            "/v1/rooms/%s/rounds/%s/votes/%s/%s"
            % (room["id"], round1["id"], first["kind"], first["id"]),
            "PUT", {"choice": "LIKE"}, token=self.token(1),
        )
        self.assertEqual(status, 200)
        status, payload, _ = api(
            "/v1/rooms/%s/rounds/%s/completion" % (room["id"], round1["id"]),
            "PUT", {}, token=self.token(1),
        )
        self.assertEqual(status, 409, payload)
        self.assertEqual(payload["error"]["code"], "INVALID_STATE")

        def vote_all(number, like_first):
            member = self.token(number)
            for index, card in enumerate(round1["candidates"]):
                choice = "LIKE" if (like_first and index == 0) else "PASS"
                status, payload, _ = api(
                    "/v1/rooms/%s/rounds/%s/votes/%s/%s"
                    % (room["id"], round1["id"], card["ref"]["kind"], card["ref"]["id"]),
                    "PUT", {"choice": choice}, token=member,
                )
                self.assertEqual(status, 200, payload)
            return self.get("/v1/rooms/" + room["id"], member)

        vote_all(2, False)
        # Vote replacement before finishing: the last choice wins.
        second = round1["candidates"][1]["ref"]
        for choice in ("LIKE", "PASS"):
            status, _, _ = api(
                "/v1/rooms/%s/rounds/%s/votes/%s/%s"
                % (room["id"], round1["id"], second["kind"], second["id"]),
                "PUT", {"choice": choice}, token=self.token(2),
            )
            self.assertEqual(status, 200)
        snapshot = vote_all(3, False)
        self.assertEqual(len(snapshot["round"]["myVotes"]), 20)
        vote_all(4, False)
        vote_all(1, True)
        for number in (1, 2, 3):
            status, payload, _ = api(
                "/v1/rooms/%s/rounds/%s/completion" % (room["id"], round1["id"]),
                "PUT", {}, token=self.token(number),
            )
            self.assertEqual(status, 200, payload)
        status, final, _ = api(
            "/v1/rooms/%s/rounds/%s/completion" % (room["id"], round1["id"]),
            "PUT", {}, token=self.token(4),
        )
        self.assertEqual(status, 200, final)
        room_now = wait_stable(self.token(1), room["id"])
        self.assertEqual(room_now["state"], "VOTING")
        self.assertEqual(room_now["round"]["memberCount"], 4)
        self.assertEqual(ids(room_now["round"]["candidates"]),
                         ["dev-swipe-event-21", "dev-swipe-event-22"])
        self.assertNotEqual(room_now["round"]["id"], round1["id"])

        status, payload, _ = api(
            "/v1/rooms/%s/rounds/%s/votes/%s/%s"
            % (room["id"], round1["id"], first["kind"], first["id"]),
            "PUT", {"choice": "PASS"}, token=self.token(2),
        )
        self.assertEqual(status, 409, payload)
        self.assertEqual(payload["error"]["code"], "STALE_ROUND")

        round2 = room_now["round"]
        for number in (1, 2, 3, 4):
            for card in round2["candidates"]:
                status, payload, _ = api(
                    "/v1/rooms/%s/rounds/%s/votes/%s/%s"
                    % (room["id"], round2["id"], card["ref"]["kind"], card["ref"]["id"]),
                    "PUT", {"choice": "PASS"}, token=self.token(number),
                )
                self.assertEqual(status, 200, payload)
        for number in (1, 2, 3, 4):
            status, payload, _ = api(
                "/v1/rooms/%s/rounds/%s/completion" % (room["id"], round2["id"]),
                "PUT", {}, token=self.token(number),
            )
            self.assertEqual(status, 200, payload)
        room_end = wait_stable(self.token(3), room["id"])
        self.assertEqual(room_end["state"], "EXHAUSTED")
        self.assertIsNone(room_end["round"])
        self.assertIsNone(room_end["result"])

    def test_ac08_outsider_available_for_isolation(self):
        email = "new@example.test"
        session = login(email)
        if not session["profileComplete"]:
            status, profile, _ = api(
                "/v1/me/registration", "PUT",
                {"displayName": "Посторонний", "birthDate": "1990-01-01"},
                token=session["accessToken"],
            )
            self.assertEqual(status, 200, profile)
            self.assertTrue(profile["profileComplete"])
        token = session["accessToken"]
        known = {s["userId"] for s in self.sessions.values()} | {
            self.phone_session["userId"]}
        self.assertNotIn(session["userId"], known)
        feed = self.get("/v1/feed/candidates?kind=EVENT", token)
        self.assertTrue(feed["items"])
        room = self.create_room(token, "AC-08 outsider")
        self.assertEqual(room["state"], "LOBBY")

        owner_room = self.create_room(self.token(1), "isolation")
        status, payload, _ = api("/v1/rooms/" + owner_room["id"], token=token)
        self.assertEqual(status, 404, payload)
        status, payload, _ = api("/v1/rooms/" + room["id"], token=self.token(1))
        self.assertEqual(status, 404, payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
