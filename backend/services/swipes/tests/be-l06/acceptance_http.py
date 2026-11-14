import json
import os
import re
import subprocess
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4

ORIGIN = "http://127.0.0.1:18197"
BACKEND = Path(__file__).resolve().parents[4]
PROJECT = os.environ.get("BE_L06_PROJECT", "srastemsya_l06_tester")
MIX = {"localDate": "2090-02-01"}
T = datetime.fromisoformat("2089-01-01T00:00:00+00:00")


def api(method, path, token=None, data=None, *, status=200, clock=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if method == "POST":
        headers["Idempotency-Key"] = str(uuid4())
    if data is not None:
        headers["Content-Type"] = "application/json"
    if clock is not None:
        headers["X-Dev-Swipes-Now"] = (T + timedelta(minutes=clock)).isoformat()
    request = Request(ORIGIN + "/v1" + path, headers=headers, method=method,
                      data=None if data is None else json.dumps(data).encode())
    try:
        response = urlopen(request, timeout=32)
    except HTTPError as error:
        response = error
    with response:
        body = response.read()
        decoded = json.loads(body) if body else None
        route = path.split("?")[0]
        code = decoded.get("code", decoded.get("error")) if isinstance(decoded, dict) else None
        if isinstance(code, dict):
            code = code.get("code")
        assert response.code == status, (method, route, response.code, status, code)
        return decoded


def login(email):
    challenge = api("POST", "/auth/challenges", data={"channel": "EMAIL", "destination": email}, status=201)
    return api("POST", f"/auth/challenges/{challenge['challengeId']}/verify", data={"code": "0427"})


def ids(room):
    return [card["ref"]["id"] for card in room["round"]["candidates"]]


def fixtures(prefix, numbers):
    return [f"{prefix}-{number:02}" for number in numbers]


def compose(*args, capture=False):
    command = ["docker", "compose", "-p", PROJECT, "-f", "compose.yaml", "-f", "compose.dev.yaml", *args]
    return subprocess.run(command, cwd=BACKEND, check=True, text=True, capture_output=capture)


def health(expected=200):
    for _ in range(30):
        try:
            response = urlopen(ORIGIN + "/swipes/health", timeout=2)
        except HTTPError as error:
            response = error
        except OSError:
            time.sleep(1)
            continue
        with response:
            if response.code == expected:
                return response.read().decode()
        time.sleep(1)
    raise AssertionError(f"swipes health did not return {expected}")


class LobbyAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sessions = [login(f"person{i}@example.test") for i in range(1, 11)]
        cls.tokens = [session["accessToken"] for session in cls.sessions]
        cls.outsider = login("new@example.test")["accessToken"]

    def get(self, room, member=0, *, clock=None, after=None, seconds=25, status=200):
        suffix = "" if after is None else f"?afterVersion={after}&waitSeconds={seconds}"
        return api("GET", f"/rooms/{room['id']}{suffix}", self.tokens[member], status=status, clock=clock)

    def lobby(self):
        room = api("POST", "/rooms", self.tokens[0], {}, status=201)
        invite = api("POST", f"/rooms/{room['id']}/invites", self.tokens[0], {}, status=201)
        token = parse_qs(urlsplit(invite["url"]).query)["token"][0]
        return room, token

    def room(self, size, filters, *, clock=None):
        room, token = self.lobby()
        for participant in self.tokens[1:size]:
            api("POST", "/room-invites/join", participant, {"token": token})
        return api("POST", f"/rooms/{room['id']}/start", self.tokens[0],
                   {"filters": {"kind": "EVENT", "budgetTotal": None, **filters}}, clock=clock)

    def vote(self, room, member, card, choice="PASS", *, clock=None, status=200):
        return api("PUT", f"/rooms/{room['id']}/rounds/{room['round']['id']}/votes/EVENT/{card}",
                   self.tokens[member], {"choice": choice}, status=status, clock=clock)

    def finish(self, room, member, *, clock=None, status=200):
        return api("PUT", f"/rooms/{room['id']}/rounds/{room['round']['id']}/completion",
                   self.tokens[member], status=status, clock=clock)

    def votes(self, room, sizes, *, clock=None):
        for member in range(room["round"]["memberCount"]):
            for card in ids(room):
                self.vote(room, member, card, "LIKE" if member < sizes.get(card, 0) else "PASS", clock=clock)

    def next(self, room, *, clock=None):
        for _ in range(50):
            room = self.get(room, clock=clock)
            if room["state"] != "REFRESHING":
                return room
            time.sleep(0.1)
        self.fail("Room remained REFRESHING")

    def complete(self, room, sizes=None, *, clock=None, parallel=False):
        self.votes(room, sizes or {}, clock=clock)
        count = room["round"]["memberCount"]
        for member in range(count - (2 if parallel else 0)):
            self.finish(room, member, clock=clock)
        if parallel:
            with ThreadPoolExecutor(2) as executor:
                list(executor.map(lambda member: self.finish(room, member, clock=clock), range(count - 2, count)))
        return self.next(room, clock=clock)

    def result(self, room, card, likes, size, basis="TOP_SCORE"):
        self.assertEqual(room["state"], "MATCHED")
        self.assertEqual(room["result"], {
            "winner": {"kind": "EVENT", "id": card},
            "basis": basis, "likes": likes, "memberCount": size,
        })
        if basis == "TOP_SCORE":
            self.assertIsNone(room["round"])

    def terminal_empty(self, room, state="EXHAUSTED"):
        self.assertEqual(room["state"], state)
        self.assertIsNone(room["round"])
        self.assertIsNone(room["result"])

    def error(self, value, expected):
        self.assertEqual(value.get("error", value).get("code"), expected)

    def test_ac01(self):
        first = self.room(5, {"categoryId": "dev-lobby-two"})
        leader = ids(first)[2]
        second = self.complete(first, {leader: 3})
        self.assertEqual(second["round"]["number"], 2)
        self.assertIsNone(second["result"])
        self.result(self.complete(second, {ids(second)[0]: 2}), leader, 3, 5)

    def test_ac02(self):
        first = self.room(3, {"categoryId": "dev-lobby-two"})
        leader = ids(first)[3]
        second = self.complete(first, {leader: 2})
        self.result(self.complete(second, {ids(second)[0]: 2}), leader, 2, 3)
        first = self.room(3, {"categoryId": "dev-lobby-short"})
        earlier, later = ids(first)[1:3]
        self.result(self.complete(first, {earlier: 2, later: 2}), earlier, 2, 3)

    def test_ac03(self):
        first = self.room(3, {"categoryId": "dev-lobby-short"})
        self.assertEqual(len(ids(first)), 4)
        self.terminal_empty(self.complete(first))

    def test_ac04(self):
        first = self.room(3, {"categoryId": "dev-lobby-short"})
        self.result(self.complete(first, {ids(first)[0]: 3}), ids(first)[0], 3, 3, "THRESHOLD")
        self.terminal_empty(self.room(2, {"categoryId": "dev-swipe-events",
                                         "budgetTotal": {"amountMinor": 0, "currency": "RUB"}}))

    def test_ac05(self):
        first = self.room(3, {"categoryId": "dev-lobby-two"})
        second = self.complete(first, {ids(first)[0]: 1})
        winner = ids(second)[2]
        self.votes(second, {winner: 2})
        self.finish(second, 0)
        before = self.get(second)
        for member in range(3):
            current = self.get(second, member)
            self.assertEqual(current["round"]["myVotes"], before["round"]["myVotes"] if member < 2 else
                             [{**vote, "choice": "PASS"} for vote in before["round"]["myVotes"]])
            self.assertEqual(set(current["round"]), {"id", "number", "expiresAt", "memberCount",
                                                  "finishedCount", "candidates", "myVotes", "myFinished"})
        with ThreadPoolExecutor(3) as executor:
            poll = executor.submit(self.get, second, after=before["version"])
            time.sleep(0.25)
            completions = [executor.submit(self.finish, second, member) for member in (1, 2)]
            for pending in completions:
                snapshot = pending.result()
                if snapshot["state"] == "MATCHED":
                    self.result(snapshot, winner, 2, 3)
            observed = poll.result()
            while observed["state"] != "MATCHED":
                self.assertGreater(observed["version"], before["version"])
                observed = self.get(second, after=observed["version"])
        self.assertGreater(observed["version"], before["version"])
        self.result(observed, winner, 2, 3)
        for member in range(3):
            self.assertEqual(self.get(second, member), observed)
            self.assertEqual(self.finish(second, member), observed)
            self.error(self.vote(second, member, winner, status=409), "STALE_ROUND")
        self.assertEqual(self.get(second), observed)

    def test_l05_01_02_03_05(self):
        first = self.room(5, MIX)
        self.assertEqual(ids(first), fixtures("dev-lobby-mix", range(1, 11)))
        second = self.complete(first, {card: 3 for card in ids(first)[::2]}, parallel=True)
        expected = [11, 14, 17, 20, 23, 26, 29, 32, 35, 13]
        self.assertEqual(second["round"]["number"], 2)
        self.assertEqual(ids(second), fixtures("dev-lobby-mix", expected))
        before = [self.get(second, member) for member in range(5)]
        for snapshot in before:
            self.assertEqual(snapshot, second)
        compose("restart", "swipes", capture=True)
        health()
        for member, snapshot in enumerate(before):
            self.assertEqual(self.get(second, member), snapshot)
        # Weights after both rounds: a=-40, b=-25, c=-5. Round 2 alone gives b=0.
        third = self.complete(second)
        self.assertEqual(third["round"]["number"], 3)
        self.assertEqual(ids(third), fixtures("dev-lobby-mix", [16, 19, 22, 25, 28, 31, 34, 12, 15, 18]))

    def test_l05_04(self):
        first = self.room(5, {"categoryId": "dev-lobby-two"})
        second = self.complete(first)
        self.assertEqual(ids(first), fixtures("dev-lobby-two", range(1, 11)))
        self.assertEqual(ids(second), fixtures("dev-lobby-two", range(11, 15)))

    def test_l05_06_l04(self):
        first = self.room(5, MIX, clock=0)
        self.assertEqual(datetime.fromisoformat(first["round"]["expiresAt"].replace("Z", "+00:00")),
                         T + timedelta(minutes=30))
        votes = {card: 3 for card in ids(first)[::2]}
        self.votes(first, votes, clock=20)
        for member in range(4):
            self.finish(first, member, clock=20)
        event = api("POST", "/events", self.tokens[5], {
            "title": "Проверка следующего пула", "description": "Событие для независимой приёмки",
            "categoryId": "dev-lobby-a", "startsAt": "2090-02-01T00:12:30Z",
            "timeZone": "Asia/Vladivostok", "admission": {"type": "OPEN"},
            "location": {"latitude": 43.1, "longitude": 131.9, "address": "Владивосток"},
            "price": {"amountMinor": 1000, "currency": "RUB"},
        }, status=201)
        self.finish(first, 4, clock=20)
        second = self.next(first, clock=20)
        expected = fixtures("dev-lobby-mix", [11, 14, 17, 20, 23, 26, 29, 32, 35])
        expected.insert(1, event["id"])
        self.assertEqual(ids(second), expected)
        self.assertEqual(datetime.fromisoformat(second["round"]["expiresAt"].replace("Z", "+00:00")),
                         T + timedelta(minutes=50))
        self.assertEqual(self.get(second, clock=30), second)
        for card in ids(second):
            self.vote(second, 1, card, "LIKE", clock=30)
        self.finish(second, 1, clock=30)
        before = [self.get(second, member, clock=30) for member in range(5)]
        compose("restart", "swipes", capture=True)
        health()
        for member, snapshot in enumerate(before):
            self.assertEqual(self.get(second, member, clock=30), snapshot)
        closed = self.get(second, clock=50)
        self.terminal_empty(closed, "CLOSED")
        self.vote(second, 0, ids(second)[0], status=409, clock=50)
        self.finish(second, 0, status=409, clock=50)
        self.assertEqual(self.get(second, clock=50), closed)

    def test_l03_01_02_04(self):
        for count, threshold in ((5, 4), (2, 2), (3, 3), (10, 7)):
            with self.subTest(count=count):
                first = self.room(count, {"categoryId": "dev-lobby-two"})
                self.assertIsNone(first["result"])
                second = self.complete(first, {ids(first)[0]: threshold - 1})
                self.assertEqual(second["state"], "VOTING")
                self.assertEqual(second["round"]["number"], 2)
                self.assertIsNone(second["result"])
                card = ids(second)[0]
                self.result(self.complete(second, {card: threshold}), card, threshold, count, "THRESHOLD")

    def test_l03_03(self):
        for first_likes, second_likes in ((4, 4), (4, 5)):
            with self.subTest(likes=(first_likes, second_likes)):
                first = self.room(5, {"categoryId": "dev-lobby-short"})
                earlier, later = ids(first)[:2]
                winner = later if second_likes > first_likes else earlier
                result = self.complete(first, {earlier: first_likes, later: second_likes}, parallel=True)
                self.result(result, winner, second_likes, 5, "THRESHOLD")
                for member in range(5):
                    self.assertEqual(self.get(first, member)["result"], result["result"])

    def test_l02_01_02_03_d03_03_04(self):
        first, token = self.lobby()
        for participant in self.tokens[1:4]:
            api("POST", "/room-invites/join", participant, {"token": token})
        first = api("POST", f"/rooms/{first['id']}/start", self.tokens[0],
                    {"filters": {"kind": "EVENT", "categoryId": "dev-swipe-events", "budgetTotal": None}})
        for member in range(4):
            snapshot = self.get(first, member)
            self.assertEqual(snapshot["members"], first["members"])
            self.assertEqual(ids(snapshot), fixtures("dev-swipe-event", range(1, 11)))
        self.assertEqual(first["round"]["number"], 1)
        self.assertEqual(len(first["members"]), 4)
        api("GET", f"/rooms/{first['id']}", self.tokens[4], status=404)
        api("POST", "/room-invites/join", self.tokens[4], {"token": token}, status=409)
        self.error(self.finish(first, 0, status=409), "INVALID_STATE")
        self.vote(first, 0, ids(first)[0], "LIKE")
        self.votes(first, {})
        self.finish(first, 0)
        self.vote(first, 0, ids(first)[0], "LIKE", status=409)
        mine = self.get(first)
        self.assertTrue(mine["round"]["myFinished"])
        self.assertEqual({entry["choice"] for entry in mine["round"]["myVotes"]}, {"PASS"})
        other = self.get(first, 1)["round"]
        self.assertEqual({vote["candidate"]["id"]: vote["choice"] for vote in other["myVotes"]},
                         dict.fromkeys(ids(first), "PASS"))
        self.assertFalse(other["myFinished"])
        for member in range(1, 4):
            self.finish(first, member)
        second = self.next(first)
        self.assertEqual(second["round"]["number"], 2)
        self.assertEqual(ids(second), fixtures("dev-swipe-event", range(11, 21)))
        third = self.complete(second)
        self.assertEqual(third["round"]["number"], 3)
        self.assertEqual(ids(third), fixtures("dev-swipe-event", [21, 22]))
        self.terminal_empty(self.complete(third))
        feed = api("GET", "/feed/candidates?kind=EVENT&categoryId=dev-swipe-events", self.tokens[0])
        self.assertEqual(len(feed["items"]), 20)
        self.assertTrue(feed["nextCursor"])

    def test_z_d03_08_09_10(self):
        room, token = self.lobby()
        room = self.get(room)
        with ThreadPoolExecutor(1) as executor:
            waiting = executor.submit(self.get, room, after=room["version"])
            time.sleep(0.25)
            api("POST", "/room-invites/join", self.tokens[1], {"token": token})
            joined = waiting.result()
            self.assertGreater(joined["version"], room["version"])
            self.assertEqual(len(joined["members"]), 2)
            self.assertNotIn(token, json.dumps(joined))
            started = api("POST", f"/rooms/{room['id']}/start", self.tokens[0],
                          {"filters": {"kind": "EVENT", "categoryId": "dev-lobby-short", "budgetTotal": None}})
            waiting = executor.submit(self.get, room, after=started["version"])
            time.sleep(0.25)
            self.vote(started, 1, ids(started)[0], "LIKE")
            updated = waiting.result()
            self.assertGreater(updated["version"], started["version"])
            self.assertEqual(updated["round"]["myVotes"], [])
            stamp = time.monotonic()
            self.assertEqual(self.get(room, after=started["version"]), updated)
            self.assertLess(time.monotonic() - stamp, 5)
            stamp = time.monotonic()
            self.assertIsNone(self.get(room, after=updated["version"], status=204))
            self.assertGreaterEqual(time.monotonic() - stamp, 24)
            waiting = executor.submit(self.get, room, after=updated["version"])
            time.sleep(0.25)
            self.vote(started, 0, ids(started)[0])
            updated = waiting.result()
            stamp = time.monotonic()
            self.get(room, 2, after=updated["version"], status=404)
            self.assertLess(time.monotonic() - stamp, 5)
            session = self.sessions[0]
            path = f"/rooms/{room['id']}?afterVersion={updated['version']}&waitSeconds=2"
            pending = executor.submit(api, "GET", path, session["accessToken"], status=401)
            time.sleep(0.25)
            api("DELETE", "/auth/session", session["accessToken"], status=204)
            self.error(pending.result(), "SESSION_EXPIRED")

    def test_int01(self):
        path = "/feed/candidates?kind=EVENT"
        self.error(api("GET", path, status=401), "UNAUTHENTICATED")
        self.error(api("GET", path, self.outsider, status=403), "PROFILE_INCOMPLETE")

    def test_int02(self):
        try:
            compose("stop", "swipes-db", capture=True)
            self.assertNotRegex(health(503), re.compile(r"postgres(?:ql)?://", re.I))
        finally:
            compose("start", "swipes-db", capture=True)
        self.assertNotRegex(health(), re.compile(r"postgres(?:ql)?://", re.I))
        logs = compose("logs", "--since", "1m", "swipes", capture=True).stdout
        self.assertFalse(re.search(r"postgres(?:ql)?://[^\s]+:[^\s]+@", logs), "Credential pattern in swipes logs")


if __name__ == "__main__":
    unittest.main(verbosity=2)
