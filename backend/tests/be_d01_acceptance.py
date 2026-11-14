"""Black-box Discovery checks against an isolated dev gateway."""
import json
import os
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

BASE = os.environ.get("D01_BASE", "http://127.0.0.1:18083")


class Discovery(unittest.TestCase):
    base = BASE

    def request(self, path, status=200, token=None, method="GET", body=None, query=None):
        headers = {}
        if token:
            headers["Authorization"] = "Bearer " + token
        if method == "POST":
            headers["Idempotency-Key"] = str(uuid4())
        payload = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            payload = json.dumps(body).encode()
        if query:
            path += "?" + urlencode(query)
        try:
            response = urlopen(Request(self.base + "/v1" + path, payload, headers, method=method), timeout=10)
        except HTTPError as error:
            response = error
        with response:
            expected = status if isinstance(status, tuple) else (status,)
            self.assertIn(response.code, expected, path.split("?", 1)[0])
            return json.load(response)

    def login(self, destination):
        challenge = self.request("/auth/challenges", 201, method="POST",
                                 body={"channel": "EMAIL", "destination": destination})
        return self.request("/auth/challenges/" + challenge["challengeId"] + "/verify",
                            method="POST", body={"code": os.environ.get("DEV_OTP", "0427")})

    def get(self, path, query=None, token=None):
        return self.request(path, token=token or self.owner["accessToken"], query=query)

    def setUp(self):
        self.owner = self.__class__.owner

    @classmethod
    def setUpClass(cls):
        client = cls()
        cls.owner = client.login("person1@example.test")
        cls.attendee = client.login("person2@example.test")
        cls.visitor = client.login("person3@example.test")
        cls.incomplete = client.login("new@example.test")

    def assert_error(self, path, status, code, token=None, query=None):
        result = self.request(path, status, token=token, query=query)
        self.assertEqual(result["error"]["code"], code, path)

    def test_ac01_home_collection_and_empty_search(self):
        home = self.get("/home")
        self.assertEqual(home, self.get("/home"))
        for key in ("quickCategories", "collections", "upcoming"):
            self.assertIsInstance(home[key], list)
        first = home["collections"][0]
        self.assertEqual(first["id"], "culture-events")
        results = self.get("/catalog/search", first["filters"])
        self.assertTrue(results["items"])
        for card in results["items"]:
            self.assertEqual(card["ref"]["kind"], "EVENT")
            self.assertEqual(card["categoryId"], "culture")
        empty = self.get("/catalog/search", {"q": str(uuid4()), **first["filters"]})
        self.assertEqual(empty, {"items": [], "nextCursor": None})

    def test_ac01_empty_home(self):
        client = Discovery()
        client.base = os.environ.get("D01_EMPTY_BASE", "http://127.0.0.1:18082")
        session = client.login("person5@example.test")
        home = client.request("/home", token=session["accessToken"])
        self.assertEqual(home, {"quickCategories": [], "collections": [], "upcoming": []})

    def test_ac03_cursor_pagination_and_binding(self):
        filters = {"kind": "EVENT", "categoryId": "outdoors"}
        map_filters = {**filters, "bbox": "131.87,43.10,131.91,43.13"}
        for path, query in (("/catalog/search", filters), ("/catalog/map", map_filters)):
            with self.subTest(path=path):
                page = self.get(path, query)
                self.assertEqual(len(page["items"]), 20)
                first_cursor = page["nextCursor"]
                self.assertTrue(first_cursor, "Pagination fixture must supply over 20 matches")
                subsequent = {**query, "cursor": first_cursor}
                second = self.get(path, subsequent)
                self.assertEqual(second["items"], self.get(path, subsequent)["items"])
                token = self.owner["accessToken"]
                for credentials, params in ((self.attendee["accessToken"], subsequent),
                                            (token, {**subsequent, "categoryId": "culture"})):
                    denied = self.request(path, (400, 409, 422), token=credentials, query=params)
                    self.assertIn(denied["error"]["code"],
                                  ("BAD_REQUEST", "CURSOR_EXPIRED", "VALIDATION_ERROR"))
                seen = {tuple(sorted(card["ref"].items())) for card in page["items"]}
                self.assertEqual(len(seen), 20)
                while page["nextCursor"]:
                    page = self.get(path, {**query, "cursor": page["nextCursor"]})
                    self.assertGreater(len(page["items"]), 0)
                    self.assertLessEqual(len(page["items"]), 20)
                    for card in page["items"]:
                        key = tuple(sorted(card["ref"].items()))
                        self.assertNotIn(key, seen)
                        seen.add(key)
                self.assertGreater(len(seen), 20)

    def test_ac02_shared_ref_and_projection(self):
        cards = self.get("/catalog/search", {"kind": "EVENT"})["items"]
        event = next(card for card in cards if card["ref"]["id"] == "dev-vlad-exhibit")
        self.assertEqual(event["ref"], {"kind": "EVENT", "id": "dev-vlad-exhibit"})
        by_ref = self.get("/catalog/EVENT/dev-vlad-exhibit")
        by_event = self.get("/events/dev-vlad-exhibit")
        self.assertEqual(by_ref, by_event)
        for key in ("location", "categoryId", "title", "admission", "startsAt"):
            self.assertEqual(by_event[key], event[key])
        self.assertEqual(by_event["id"], event["ref"]["id"])
        categories = {cat["id"]: cat for cat in self.get("/catalog/categories")["items"]}
        self.assertIn("EVENT", categories[event["categoryId"]]["kinds"])

    def test_ac03_bounds_types_publication(self):
        for kind, resource in (("EVENT", "dev-vlad-exhibit"), ("PLACE", "dev-vlad-museum"),
                               ("ACTIVITY", "dev-vlad-walk")):
            full = self.get("/catalog/map", {"kind": kind, "bbox": "131.87,43.10,131.91,43.13"})
            card = next(card for card in full["items"] if card["ref"]["id"] == resource)
            self.assertTrue(all(item["ref"]["kind"] == kind for item in full["items"]))
            detail = self.get(f"/catalog/{kind}/{resource}")
            if kind != "EVENT":
                self.assertEqual(detail["card"], card)
            lon = card["location"]["longitude"]
            lat = card["location"]["latitude"]
            boundary = self.get("/catalog/map", {"kind": kind, "bbox": f"{lon},{lat},{lon+0.01},{lat+0.01}"})
            self.assertIn(card, boundary["items"])
            distant = self.get("/catalog/map", {"kind": kind, "bbox": "0,0,1,1"})
            self.assertEqual(distant, {"items": [], "nextCursor": None})
        for path in ("/catalog/EVENT/dev-vlad-draft", "/events/dev-vlad-draft",
                     "/catalog/PLACE/dev-vlad-exhibit"):
            self.assert_error(path, 404, "NOT_FOUND", self.owner["accessToken"])
        for path, query in (("/home", {}), ("/catalog/search", {"kind": "EVENT"}),
                            ("/catalog/map", {"kind": "EVENT", "bbox": "131.87,43.10,131.91,43.13"})):
            page = self.get(path, query)
            self.assertNotIn("dev-vlad-draft", [card["ref"]["id"] for card in page.get("items", page.get("upcoming"))])

    def test_ac03_invalid_parameters(self):
        token = self.owner["accessToken"]
        for query in ({}, {"kind": "EVENT"}, {"bbox": "0,0,1,1"},
                      {"kind": "EVENT", "bbox": "1,0,0,1"}, {"kind": "EVENT", "bbox": "0,0,181,91"},
                      {"kind": "EVENT", "bbox": "NaN,0,1,1"}, {"kind": "BOGUS", "bbox": "0,0,1,1"}):
            with self.subTest(query=query):
                self.assert_error("/catalog/map", 422, "VALIDATION_ERROR", token, query)

    def test_ac03_ac07_per_viewer_and_capacity(self):
        path = "/catalog/EVENT/dev-vlad-workshop"
        for session, role, can_register in ((self.owner, "ORGANIZER", False),
                                            (self.attendee, "ATTENDEE", False),
                                            (self.visitor, "VISITOR", True),
                                            (self.owner, "ORGANIZER", False)):
            token = session["accessToken"]
            event = self.get(path, token=token)
            self.assertEqual(event, self.get("/events/dev-vlad-workshop", token=token))
            self.assertEqual(event["timeZone"], "Asia/Vladivostok")
            self.assertEqual(event["phase"], "UPCOMING")
            admission = event["admission"]
            self.assertEqual(admission["type"], "REGISTRATION")
            self.assertEqual(admission["confirmedCount"], 1)
            self.assertEqual(admission["remainingCount"], admission["capacity"] - 1)
            viewer = event["viewer"]
            self.assertEqual(viewer["role"], role)
            self.assertEqual(viewer["canRegister"], can_register)
            for flag in ("canReadChat", "canPostChat", "saved"):
                self.assertIs(viewer[flag], False)
            if role == "ATTENDEE":
                self.assertEqual(viewer["registration"]["status"], "CONFIRMED")
                self.assertEqual(viewer["registration"]["userId"], session["userId"])
            else:
                self.assertIsNone(viewer["registration"])

    def test_ac04_and_ac05_access_and_registration(self):
        for path in ("/home", "/catalog/categories", "/catalog/search", "/catalog/map",
                     "/catalog/EVENT/dev-vlad-exhibit", "/events/dev-vlad-exhibit", "/rooms"):
            with self.subTest(path=path):
                self.assert_error(path, 401, "UNAUTHENTICATED")
                if not self.incomplete["profileComplete"]:
                    self.assert_error(path, 403, "PROFILE_INCOMPLETE", self.incomplete["accessToken"])
        token = self.incomplete["accessToken"]
        if self.incomplete["profileComplete"]:
            self.skipTest("Initial profile completion requires a clean stand")
        profile = self.request("/me/registration", token=token, method="PUT",
                               body={"displayName": "D01 test", "birthDate": "1994-05-06"})
        self.assertIs(profile["profileComplete"], True)
        self.assertIsInstance(self.get("/rooms", token=token)["items"], list)
        self.assertIsInstance(self.get("/home", token=token)["collections"], list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
