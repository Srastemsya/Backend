import concurrent.futures
import json
import os
import time
import unittest
import uuid
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


BASE = os.getenv("L03_BASE", "http://127.0.0.1:18943")
NOW = "2089-01-01T00:00:00Z"


def request(path, method="GET", actor=None, data=None):
    headers = {"X-Dev-Swipes-Now": NOW}
    if actor:
        headers["Authorization"] = "Bearer " + actor["accessToken"]
    if method == "POST":
        headers["Idempotency-Key"] = str(uuid.uuid4())
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode()
    try:
        response = urlopen(Request(BASE + path, body, headers, method=method), timeout=35)
    except HTTPError as error:
        response = error
    with response:
        raw = response.read()
        return response.status, json.loads(raw) if raw else None


class Acceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.actors = [cls.login(f"person{i}") for i in range(1, 11)]
        cls.outsider = cls.login("new")

    @staticmethod
    def login(name):
        status, challenge = request("/v1/auth/challenges", "POST", data={
            "channel": "EMAIL", "destination": name + "@example.test",
        })
        if status != 201:
            raise RuntimeError(f"challenge status {status} for dev fixture {name}")
        status, session = request(
            f"/v1/auth/challenges/{challenge['challengeId']}/verify",
            "POST", data={"code": os.getenv("DEV_OTP", "0427")},
        )
        if status != 200:
            raise RuntimeError(f"verification status {status} for dev fixture {name}")
        return session

    def call(self, path, method="GET", actor=None, data=None, status=200, code=None):
        actual, body = request(path, method, actor, data)
        self.assertEqual(actual, status, f"{method} {path.split('?')[0]}")
        if code:
            self.assertEqual(body["error"]["code"], code)
        return body

    def lobby(self, count):
        host = self.actors[0]
        room = self.call("/v1/rooms", "POST", host, {}, 201)
        self.assertIsNone(room["result"])
        path = "/v1/rooms/" + room["id"]
        invite = self.call(path + "/invites", "POST", host, {}, 201)
        token = parse_qs(urlparse(invite["url"]).query)["token"][0]
        for actor in self.actors[1:count]:
            self.join(token, actor)
        return path, token

    def join(self, token, actor, status=200):
        return self.call("/v1/room-invites/join", "POST", actor, {"token": token}, status)

    def start(self, path, category="dev-lobby-two"):
        return self.call(path + "/start", "POST", self.actors[0], {
            "filters": {"kind": "EVENT", "categoryId": category, "budgetTotal": None},
        })

    @staticmethod
    def refs(room):
        return [card["ref"] for card in room["round"]["candidates"]]

    @staticmethod
    def round_path(path, room):
        return path + "/rounds/" + room["round"]["id"]

    def vote(self, round_path, actor, ref, choice, status=200):
        return self.call(
            f"{round_path}/votes/{ref['kind']}/{ref['id']}", "PUT", actor,
            {"choice": choice}, status,
        )

    def finish(self, round_path, actor, status=200, code=None):
        return self.call(round_path + "/completion", "PUT", actor, status=status, code=code)

    def settle(self, path, room, count, likes, parallel=False):
        self.assertIsNone(room["result"])
        round_path = self.round_path(path, room)
        actors = self.actors[:count]
        for index, actor in enumerate(actors):
            for position, ref in enumerate(self.refs(room)):
                self.vote(round_path, actor, ref, "LIKE" if index < likes.get(position, 0) else "PASS")
        if parallel:
            for actor in actors[:-2]:
                self.finish(round_path, actor)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                list(pool.map(lambda actor: self.finish(round_path, actor), actors[-2:]))
        else:
            for actor in actors:
                self.finish(round_path, actor)
        for _ in range(20):
            current = self.call(path, actor=actors[0])
            if current["state"] != "REFRESHING":
                return current
            time.sleep(0.1)
        self.fail("room stayed REFRESHING")

    def assert_match(self, room, ref, likes, count):
        self.assertEqual(room["state"], "MATCHED")
        self.assertEqual(room["result"], {
            "winner": ref, "basis": "THRESHOLD", "likes": likes, "memberCount": count,
        })

    def assert_next(self, room, number):
        self.assertEqual(room["state"], "VOTING")
        self.assertIsNone(room["result"])
        self.assertEqual(room["round"]["number"], number)

    def test_ac01_and_ac04_five_members(self):
        path, _ = self.lobby(5)
        first = self.start(path)
        second = self.settle(path, first, 5, {0: 3})
        self.assert_next(second, 2)
        self.assert_match(self.settle(path, second, 5, {0: 4}), self.refs(second)[0], 4, 5)

    def test_ac02_boundaries(self):
        for count, threshold in ((2, 2), (3, 3), (10, 7)):
            with self.subTest(count=count):
                path, _ = self.lobby(count)
                first = self.start(path)
                second = self.settle(path, first, count, {0: threshold - 1})
                self.assert_next(second, 2)
                self.assert_match(
                    self.settle(path, second, count, {0: threshold}),
                    self.refs(second)[0], threshold, count,
                )

    def test_ac03_parallel_finish_ties_and_ranking(self):
        for likes, winner in (({0: 4, 1: 4}, 0), ({0: 4, 1: 5}, 1)):
            with self.subTest(likes=likes):
                path, _ = self.lobby(5)
                first = self.start(path)
                final = self.settle(path, first, 5, likes, parallel=True)
                self.assert_match(final, self.refs(first)[winner], likes[winner], 5)
                for actor in self.actors[:5]:
                    observed = self.call(path, actor=actor)
                    self.assertEqual(observed["version"], final["version"])
                    self.assertEqual(observed["result"], final["result"])
                    self.assertEqual(observed["state"], "MATCHED")
                    repeated = self.finish(self.round_path(path, first), actor)
                    self.assertEqual(repeated["version"], final["version"])
                    self.assertEqual(repeated["result"], final["result"])

    def test_ac05_l02_01_to_03_pools_and_feed(self):
        path, _ = self.lobby(4)
        room = self.start(path, "dev-swipe-events")
        for number, (begin, end) in enumerate(((1, 11), (11, 21), (21, 23)), 1):
            self.assert_next(room, number)
            expected = [{"kind": "EVENT", "id": f"dev-swipe-event-{i:02}"} for i in range(begin, end)]
            for actor in self.actors[:4]:
                observed = self.call(path, actor=actor)
                self.assertEqual(observed["round"]["memberCount"], 4)
                self.assertEqual(observed["round"]["id"], room["round"]["id"])
                self.assertEqual(self.refs(observed), expected)
            room = self.settle(path, room, 4, {})
        self.assertEqual(room["state"], "EXHAUSTED")
        self.assertIsNone(room["round"])
        self.assertIsNone(room["result"])
        feed = self.call("/v1/feed/candidates?kind=EVENT&categoryId=dev-swipe-events", actor=self.actors[0])
        self.assertEqual(len(feed["items"]), 20)
        self.assertTrue(feed["nextCursor"])

    def test_ac05_d03_03_and_04_access_and_votes(self):
        path, token = self.lobby(4)
        room = self.start(path, "dev-lobby-short")
        for actor in self.actors[:4]:
            observed = self.call(path, actor=actor)
            self.assertEqual(self.refs(observed), self.refs(room))
            self.assertEqual(observed["round"]["memberCount"], 4)
        self.call(path, actor=self.actors[4], status=404, code="NOT_FOUND")
        self.join(token, self.actors[4], status=409)
        host = self.actors[0]
        round_path = self.round_path(path, room)
        self.finish(round_path, host, status=409, code="INVALID_STATE")
        refs = self.refs(room)
        self.vote(round_path, host, refs[0], "PASS")
        self.vote(round_path, host, refs[0], "LIKE")
        for ref in refs[1:]:
            self.vote(round_path, host, ref, "PASS")
        self.finish(round_path, host)
        self.vote(round_path, host, refs[0], "PASS", status=409)
        observed = self.call(path, actor=host)["round"]
        self.assertTrue(observed["myFinished"])
        self.assertEqual({vote["candidate"]["id"]: vote["choice"] for vote in observed["myVotes"]},
                         {ref["id"]: "LIKE" if i == 0 else "PASS" for i, ref in enumerate(refs)})
        other = self.call(path, actor=self.actors[1])["round"]
        self.assertFalse(other["myFinished"])
        self.assertEqual(other["myVotes"], [])

    def test_ac05_d03_08_and_09_poll_updates(self):
        path, token = self.lobby(1)
        host, guest = self.actors[:2]
        current = self.call(path, actor=host)
        self.assertEqual(len(current["members"]), 1)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            waiting = pool.submit(self.call, path + f"?afterVersion={current['version']}&waitSeconds=25",
                                  actor=host)
            time.sleep(0.5)
            self.assertFalse(waiting.done())
            self.join(token, guest)
            joined = waiting.result(timeout=5)
        self.assertGreater(joined["version"], current["version"])
        self.assertEqual(len(joined["members"]), 2)
        self.assertFalse(token in json.dumps(joined), "invite token leaked into room snapshot")
        first = self.start(path, "dev-lobby-short")
        poll = path + f"?afterVersion={first['version']}&waitSeconds=25"
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            waiting = pool.submit(self.call, poll, actor=host)
            time.sleep(0.5)
            self.assertFalse(waiting.done())
            self.vote(self.round_path(path, first), guest, self.refs(first)[0], "LIKE")
            updated = waiting.result(timeout=5)
        self.assertGreater(updated["version"], first["version"])
        self.assertEqual(updated["round"]["myVotes"], [])
        before = time.monotonic()
        repeat = self.call(poll, actor=host)
        self.assertLess(time.monotonic() - before, 2)
        self.assertEqual(repeat["version"], updated["version"])

    def test_z_ac05_d03_10_poll_timeout_and_revocation(self):
        path, _ = self.lobby(2)
        host = self.actors[0]
        current = self.call(path, actor=host)
        poll = path + f"?afterVersion={current['version']}&waitSeconds=25"
        before = time.monotonic()
        self.call(poll, actor=self.actors[4], status=404, code="NOT_FOUND")
        self.assertLess(time.monotonic() - before, 2)
        before = time.monotonic()
        self.assertIsNone(self.call(poll, actor=host, status=204))
        self.assertGreaterEqual(time.monotonic() - before, 24)
        self.assertIsNone(self.call(poll.replace("waitSeconds=25", "waitSeconds=1"), actor=host, status=204))
        guest = self.actors[1]
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            waiting = pool.submit(self.call, poll.replace("waitSeconds=25", "waitSeconds=2"),
                                  actor=guest, status=401, code="SESSION_EXPIRED")
            time.sleep(0.5)
            self.assertFalse(waiting.done())
            self.call("/v1/auth/session", "DELETE", guest, status=204)
            waiting.result(timeout=5)

    def test_ac05_int01_protected_routes(self):
        self.assertFalse(self.outsider["profileComplete"])
        path, _ = self.lobby(1)
        for route in (path, "/v1/feed/candidates?kind=EVENT&categoryId=dev-lobby-short"):
            with self.subTest(route=route):
                self.call(route, status=401, code="UNAUTHENTICATED")
                self.call(route, actor=self.outsider, status=403, code="PROFILE_INCOMPLETE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
