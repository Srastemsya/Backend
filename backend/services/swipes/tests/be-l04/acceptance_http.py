import concurrent.futures
import datetime as dt
import json
import os
import subprocess
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


BASE = "http://127.0.0.1:18094"
T = "2089-01-01T00:{:02d}:00Z"
FILTER = {"kind": "EVENT", "categoryId": "dev-swipe-events", "budgetTotal": None}
BACKEND = Path(__file__).resolve().parents[4]


def request(method, path, token=None, body=None, now=None, expected=200):
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    if method == "POST":
        headers["Idempotency-Key"] = str(uuid.uuid4())
    if now:
        headers["X-Dev-Swipes-Now"] = now
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data, headers, method=method)
    try:
        response = urllib.request.urlopen(req, timeout=32)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        raw = response.read()
        if response.status != expected:
            code = None
            if raw and response.headers.get("Content-Type", "").startswith("application/json"):
                code = json.loads(raw).get("error", {}).get("code")
            raise AssertionError((method, response.status, expected, code))
    return json.loads(raw) if raw else None


def api(method, path, token=None, body=None, now=None, expected=200):
    return request(method, "/v1" + path, token, body, now, expected)


def login(email):
    challenge = api("POST", "/auth/challenges", body={"channel": "EMAIL", "destination": email}, expected=201)
    return api("POST", "/auth/challenges/" + challenge["challengeId"] + "/verify", body={"code": "0427"})


def compose(*args):
    command = ["docker", "compose", "-p", "srastemsya_l04", "-f", "compose.yaml", "-f", "compose.dev.yaml"]
    return subprocess.run(command + list(args), cwd=BACKEND, env={**os.environ, "NGINX_PORT": "18094"},
                          capture_output=True, check=True, text=True).stdout


class Acceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with concurrent.futures.ThreadPoolExecutor() as workers:
            sessions = list(workers.map(login, [f"person{i}@example.test" for i in range(1, 11)] + ["new@example.test"]))
        cls.people = [s["accessToken"] for s in sessions[:10]]
        cls.incomplete = sessions[10]["accessToken"]

    def read(self, room, index=0, now=None, after=None, wait=25, expected=200):
        query = "" if after is None else f"?afterVersion={after}&waitSeconds={wait}"
        return api("GET", room + query, self.people[index], now=now, expected=expected)

    def lobby(self):
        snap = api("POST", "/rooms", self.people[0], {}, expected=201)
        room = "/rooms/" + snap["id"]
        invite = api("POST", room + "/invites", self.people[0], {}, expected=201)
        token = urllib.parse.parse_qs(urllib.parse.urlsplit(invite["url"]).query)["token"][0]
        return room, {"token": token}

    def join(self, invite, index, expected=200):
        return api("POST", "/room-invites/join", self.people[index], invite, expected=expected)

    def start(self, count, now=None):
        room, invite = self.lobby()
        for index in range(1, count):
            self.join(invite, index)
        return room, api("POST", room + "/start", self.people[0], {"filters": FILTER}, now), invite

    def vote(self, room, snap, index, card=0, choice="PASS", now=None, expected=200):
        round_data = snap["round"]
        candidate = round_data["candidates"][card]
        path = f'{room}/rounds/{round_data["id"]}/votes/EVENT/{candidate["ref"]["id"]}'
        return api("PUT", path, self.people[index], {"choice": choice}, now, expected)

    def finish(self, room, snap, index, now=None, expected=200):
        return api("PUT", f'{room}/rounds/{snap["round"]["id"]}/completion',
                   self.people[index], now=now, expected=expected)

    def pass_round(self, room, snap, count, likes=(), now=None, parallel=False):
        for index in range(count):
            for card in range(len(snap["round"]["candidates"])):
                self.vote(room, snap, index, card, "LIKE" if card < len(likes) and index < likes[card] else "PASS", now)
        for index in range(count - (2 if parallel else 1)):
            self.finish(room, snap, index, now)
        if parallel:
            with concurrent.futures.ThreadPoolExecutor() as workers:
                results = list(workers.map(lambda i: self.finish(room, snap, i, now), range(count - 2, count)))
            for result in results:
                self.assertIn(result["state"], ("VOTING", "MATCHED"))
        else:
            self.finish(room, snap, count - 1, now)
        return self.read(room, now=now)

    def closed(self, snap):
        self.assertEqual((snap["state"], snap["round"], snap["result"]), ("CLOSED", None, None))

    def test_ac_01_to_04_deadline_and_restart(self):
        room, first, _ = self.start(2, T.format(0))
        self.assertEqual(first["round"]["expiresAt"], T.format(30))
        second = self.pass_round(room, first, 2, now=T.format(20))
        self.assertEqual((second["round"]["number"], second["round"]["expiresAt"]), (2, T.format(50)))
        self.assertGreater(second["version"], first["version"])
        self.assertEqual(self.read(room, now=T.format(30)), second)
        for card in range(len(second["round"]["candidates"])):
            self.vote(room, second, 0, card, now=T.format(31))
        self.finish(room, second, 0, T.format(31))
        self.vote(room, second, 1, choice="LIKE", now=T.format(31))
        before = [self.read(room, i, T.format(35)) for i in range(2)]
        self.assertGreater(before[0]["version"], second["version"])
        self.assertTrue(before[0]["round"]["myFinished"])
        self.assertFalse(before[1]["round"]["myFinished"])
        compose("restart", "swipes")
        self.wait_health(200)
        self.assertEqual([self.read(room, i, T.format(35)) for i in range(2)], before)
        closed = self.read(room, now=T.format(50))
        self.closed(closed)
        self.assertGreater(closed["version"], before[0]["version"])
        self.vote(room, second, 1, now=T.format(50), expected=409)
        self.finish(room, second, 1, T.format(50), expected=409)
        self.assertEqual(self.read(room, now=T.format(51)), closed)

    def test_ac_03_deadline_wakes_poll_without_other_request(self):
        deadline = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=9)
        start = deadline - dt.timedelta(minutes=30)
        room, first, _ = self.start(2, start.isoformat())
        self.assertEqual(dt.datetime.fromisoformat(first["round"]["expiresAt"].replace("Z", "+00:00")), deadline)
        self.assertGreater((deadline - dt.datetime.now(dt.timezone.utc)).total_seconds(), 3)
        closed = self.read(room, after=first["version"], wait=25)
        lag = (dt.datetime.now(dt.timezone.utc) - deadline).total_seconds()
        self.assertGreaterEqual(lag, 0)
        self.assertLess(lag, 2)
        self.closed(closed)
        self.assertGreater(closed["version"], first["version"])
        self.assertEqual(self.read(room), closed)

    def test_l03_01_02_04_thresholds(self):
        for count, threshold in ((2, 2), (3, 3), (5, 4), (10, 7)):
            with self.subTest(count=count):
                room, first, _ = self.start(count)
                self.assertIsNone(first["result"])
                second = self.pass_round(room, first, count, (threshold - 1,))
                self.assertEqual((second["state"], second["round"]["number"], second["result"]), ("VOTING", 2, None))
                match = self.pass_round(room, second, count, (threshold,))
                self.check_winner(match, second, count, threshold, 0)

    def check_winner(self, match, snap, count, likes, card):
        self.assertEqual(match["state"], "MATCHED")
        self.assertEqual(match["result"], {"winner": {"kind": "EVENT", "id": snap["round"]["candidates"][card]["ref"]["id"]},
                                          "basis": "THRESHOLD", "likes": likes, "memberCount": count})

    def test_l03_03_parallel_tie_and_stronger_winner(self):
        for likes, card in (((4, 4), 0), ((3, 4), 1)):
            with self.subTest(likes=likes):
                room, first, _ = self.start(4)
                match = self.pass_round(room, first, 4, likes, parallel=True)
                self.check_winner(match, first, 4, 4, card)
                for i in range(4):
                    current = self.read(room, i)
                    self.assertEqual((current["state"], current["version"], current["result"]),
                                     (match["state"], match["version"], match["result"]))

    def test_l02_01_02_and_d03_03_pools_and_members(self):
        room, snap, invite = self.start(4)
        self.assertEqual(len(snap["members"]), 4)
        for i in range(4):
            peer = self.read(room, i)
            self.assertEqual(peer["members"], snap["members"])
            self.assertEqual(peer["round"]["candidates"], snap["round"]["candidates"])
            self.assertEqual(peer["round"]["memberCount"], 4)
        self.assertEqual(self.read(room, 4, expected=404)["error"]["code"], "NOT_FOUND")
        self.join(invite, 4, expected=409)
        for number, begin, end in ((1, 1, 11), (2, 11, 21), (3, 21, 23)):
            self.assertEqual(snap["round"]["number"], number)
            self.assertEqual([c["ref"]["id"] for c in snap["round"]["candidates"]],
                             [f"dev-swipe-event-{i:02}" for i in range(begin, end)])
            snap = self.pass_round(room, snap, 4)
        self.assertEqual((snap["state"], snap["round"], snap["result"]), ("EXHAUSTED", None, None))

    def test_l02_03_feed_page(self):
        page = api("GET", "/feed/candidates?kind=EVENT&categoryId=dev-swipe-events", self.people[0])
        self.assertEqual(len(page["items"]), 20)
        self.assertTrue(page["nextCursor"])

    def test_d03_04_08_09_completion_and_polls(self):
        room, invite = self.lobby()
        lobby = self.read(room)
        with concurrent.futures.ThreadPoolExecutor() as workers:
            poll = workers.submit(self.read, room, after=lobby["version"])
            time.sleep(.3)
            self.join(invite, 1)
            joined = poll.result()
            self.assertGreater(joined["version"], lobby["version"])
            self.assertEqual(len(joined["members"]), 2)
            self.assertNotIn(invite["token"], json.dumps(joined))
            first = api("POST", room + "/start", self.people[0], {"filters": FILTER})
            error = self.finish(room, first, 0, expected=409)
            self.assertEqual(error["error"]["code"], "INVALID_STATE")
            poll = workers.submit(self.read, room, 1, after=first["version"])
            time.sleep(.3)
            self.vote(room, first, 0, choice="LIKE")
            peer = poll.result()
            self.assertGreater(peer["version"], first["version"])
            self.assertEqual(peer["round"]["myVotes"], [])
            started = time.monotonic()
            self.assertEqual(self.read(room, 1, after=first["version"]), peer)
            self.assertLess(time.monotonic() - started, 2)
        for card in range(len(first["round"]["candidates"])):
            self.vote(room, first, 0, card)
        self.finish(room, first, 0)
        finished = self.read(room)
        self.assertTrue(finished["round"]["myFinished"])
        self.assertEqual([v["choice"] for v in finished["round"]["myVotes"]], ["PASS"] * 10)
        self.vote(room, first, 0, choice="LIKE", expected=409)
        self.assertEqual(self.read(room), finished)
        self.assertEqual(self.read(room, 1)["round"]["myVotes"], [])

    def test_z_d03_10_idle_unauthorized_and_revoked(self):
        room, invite = self.lobby()
        snap = self.read(room)
        started = time.monotonic()
        self.assertIsNone(self.read(room, after=snap["version"], expected=204))
        self.assertGreaterEqual(time.monotonic() - started, 24)
        self.assertIsNone(self.read(room, after=snap["version"], wait=1, expected=204))
        started = time.monotonic()
        self.assertEqual(self.read(room, 5, after=snap["version"], expected=404)["error"]["code"], "NOT_FOUND")
        self.assertLess(time.monotonic() - started, 2)
        self.join(invite, 9)
        snap = self.read(room)
        with concurrent.futures.ThreadPoolExecutor() as workers:
            poll = workers.submit(self.read, room, 9, after=snap["version"], wait=2, expected=401)
            time.sleep(.3)
            api("DELETE", "/auth/session", self.people[9], expected=204)
            self.assertEqual(poll.result()["error"]["code"], "SESSION_EXPIRED")

    def test_int_01_access(self):
        for path in ("/feed/candidates?kind=EVENT", "/rooms"):
            method = "POST" if path == "/rooms" else "GET"
            body = {} if method == "POST" else None
            self.assertEqual(api(method, path, body=body, expected=401)["error"]["code"], "UNAUTHENTICATED")
            self.assertEqual(api(method, path, self.incomplete, body, expected=403)["error"]["code"], "PROFILE_INCOMPLETE")

    def wait_health(self, expected):
        for _ in range(45):
            try:
                return request("GET", "/swipes/health", expected=expected)
            except (AssertionError, OSError):
                time.sleep(.5)
        self.fail(f"Health did not return {expected}")

    def test_int_02_owned_database_readiness(self):
        compose("stop", "swipes-db")
        try:
            response = self.wait_health(503)
            logs = compose("logs", "--since", "1m", "--no-color", "swipes")
            self.assertNotRegex(json.dumps(response) + logs, r"(?i)(postgres(?:ql)?://\S+@|password\s*[=:]\s*\S+)")
        finally:
            compose("start", "swipes-db")
            self.wait_health(200)
