#!/usr/bin/env python3
"""INT-00 black-box check for a clean BE-L01 Compose stand.

Complements be_l01_acceptance.py: runs on a freshly created project of the
BE-L01 build and verifies readiness, applied migrations/dev data without
duplicates, registration/afisha/rooms through Nginx and unpublished internal
ports. Public HTTP and Compose process metadata only; no source access.

Environment:
  BE_L01_BASE_URL         base URL via Nginx
  BE_L01_COMPOSE_PROJECT  Compose project of the clean stand
"""
import datetime
import json
import os
import subprocess
import unittest
import urllib.parse
import uuid

from be_l01_acceptance import api, ids, login, read_all

BASE = os.environ.get("BE_L01_BASE_URL", "http://127.0.0.1:18090").rstrip("/")
PROJECT = os.environ.get("BE_L01_COMPOSE_PROJECT", "")


class Int00(unittest.TestCase):
    token = None

    @classmethod
    def setUpClass(cls):
        session = login("new@example.test")
        if not session["profileComplete"]:
            status, profile, _ = api(
                "/v1/me/registration", "PUT",
                {"displayName": "Проверка INT-00", "birthDate": "1990-01-01"},
                token=session["accessToken"],
            )
            if status != 200:
                raise AssertionError("registration -> %s %s" % (status, profile))
        cls.session = session
        cls.token = session["accessToken"]

    def test_health_and_registration_paths(self):
        for path in ("/identity/health", "/catalog/health", "/swipes/health"):
            status, payload, _ = api(path)
            self.assertEqual(status, 200, "%s -> %s %s" % (path, status, payload))
        status, profile, _ = api("/v1/me", token=self.token)
        self.assertEqual(status, 200)
        self.assertTrue(profile["profileComplete"])
        status, home, _ = api("/v1/home", token=self.token)
        self.assertEqual(status, 200)
        status, events, _ = api("/v1/events", token=self.token)
        self.assertEqual(status, 200)
        self.assertTrue(events["items"])

    def test_dev_data_applied_once(self):
        mixed, pages = read_all(self.token, "kind=EVENT&localDate=2090-02-01")
        self.assertEqual(pages, 2)
        self.assertEqual(ids(mixed), ["dev-lobby-mix-%02d" % n for n in range(1, 36)])
        for category, expected in (
            ("dev-lobby-short", ["dev-lobby-short-%02d" % n for n in range(1, 5)]),
            ("dev-lobby-two", ["dev-lobby-two-%02d" % n for n in range(1, 15)]),
            ("dev-swipe-events", ["dev-swipe-event-%02d" % n for n in range(1, 23)]),
        ):
            items, _ = read_all(self.token, "kind=EVENT&categoryId=" + category)
            self.assertEqual(ids(items), expected, category)
            self.assertEqual(len(set(ids(items))), len(expected), category)
        places, _ = read_all(self.token, "kind=PLACE&categoryId=dev-swipe-places")
        self.assertEqual(ids(places), ["dev-swipe-place-%02d" % n for n in range(1, 23)])

    def test_rooms_and_internal_ports(self):
        status, room, _ = api(
            "/v1/rooms", "POST", {"name": "INT-00"}, token=self.token,
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )
        self.assertEqual(status, 201, room)
        self.assertEqual(room["state"], "LOBBY")

        if not PROJECT:
            return
        names = subprocess.run(
            ["docker", "ps", "--filter",
             "label=com.docker.compose.project=" + PROJECT,
             "--format", "{{.Names}}"],
            check=True, capture_output=True, text=True,
        ).stdout
        containers = [line.strip() for line in names.splitlines() if line.strip()]
        self.assertTrue(containers, "no containers for " + PROJECT)
        for name in containers:
            if name.endswith(("-identity-db-1", "-catalog-db-1", "-swipes-db-1",
                              "-redis-1", "-kafka-1")):
                out = subprocess.run(
                    ["docker", "inspect", "--format",
                     "{{json .HostConfig.PortBindings}}", name],
                    check=True, capture_output=True, text=True,
                ).stdout.strip()
                self.assertIn(out, ("{}", "null"),
                              "%s publishes ports: %s" % (name, out))
        nginx = [n for n in containers if n.endswith("-nginx-1")]
        self.assertEqual(len(nginx), 1)
        out = subprocess.run(
            ["docker", "inspect", "--format",
             "{{json .HostConfig.PortBindings}}", nginx[0]],
            check=True, capture_output=True, text=True,
        ).stdout
        for entries in json.loads(out).values():
            for entry in entries:
                self.assertEqual(entry.get("HostIp"), "127.0.0.1", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
