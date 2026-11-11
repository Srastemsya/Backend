"""Runtime failure injection on an isolated, explicitly selected Compose project."""
import json
import os
from pathlib import Path
import re
import subprocess
import time
import unittest
import urllib.error
import urllib.request

import be_d00_acceptance as http


BACKEND = Path(__file__).resolve().parents[1]
SERVICES = ("nginx", "identity", "catalog", "swipes", "redis", "kafka")
APPS = ("identity", "catalog", "swipes")


def compose(*args, dev=True, timeout=150, default_port=False):
    project = os.environ["D00_PROJECT"]
    if not project.startswith("be-d00-acceptance"):
        raise ValueError("Select an isolated BE-D00 acceptance Compose project")
    command = ["docker", "compose", "-p", project, "-f", "compose.yaml"]
    if dev:
        command += ["-f", "compose.dev.yaml"]
    env = os.environ.copy()
    if default_port:
        env.pop("NGINX_PORT", None)
    return subprocess.run(command + list(args), cwd=BACKEND, env=env, capture_output=True,
                          text=True, timeout=timeout, check=False)


def readiness(service):
    base_url = os.getenv("D00_URL", "http://127.0.0.1:8080")
    path = os.environ["D00_HEALTH_" + service.upper()]
    try:
        response = urllib.request.urlopen(base_url + path, timeout=4)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, response.read().decode()


class Runtime(unittest.TestCase):
    def compose_ok(self, *args):
        result = compose(*args)
        self.assertEqual(result.returncode, 0, "Compose operation failed: " + " ".join(args[:2]))
        return result.stdout

    def wait_ready(self, service, expected):
        deadline = time.monotonic() + 45
        while True:
            status, body = readiness(service)
            if status == expected or time.monotonic() >= deadline:
                self.assertEqual(status, expected, service)
                return body
            time.sleep(0.5)

    def test_ac04_mock_outside_dev(self):
        env_override = os.environ["D00_MOCK_OVERRIDE"]
        result = compose("run", "--rm", "--no-deps", "-e", env_override, "-e", "APP_ENV=production",
                         "identity", dev=False,
                         timeout=25)
        self.assertNotEqual(result.returncode, 0)
        output = result.stdout + result.stderr
        self.assertRegex(output.lower(), r"mock[^\n]{0,120}\bdev\b|\bdev\b[^\n]{0,120}mock")

    def test_ac05_topology_and_repeat(self):
        output = self.compose_ok("ps", "--format", "json")
        try:
            entries = json.loads(output)
        except json.JSONDecodeError:
            entries = [json.loads(line) for line in output.splitlines() if line]
        if isinstance(entries, dict):
            entries = [entries]
        by_service = {entry["Service"]: entry for entry in entries}
        required = set(SERVICES) | {f"{service}-db" for service in APPS}
        self.assertTrue(required <= set(by_service), "required Compose services missing")
        for service in required:
            self.assertEqual(by_service[service]["State"], "running", service)
        published = [
            (entry["Service"], port.get("URL"), port.get("PublishedPort"))
            for entry in entries for port in entry.get("Publishers") or []
            if port.get("PublishedPort")
        ]
        bound_port = int(os.getenv("NGINX_PORT", "8080"))
        self.assertEqual(published, [("nginx", "127.0.0.1", bound_port)])
        config = compose("config", "--format", "json", default_port=True)
        self.assertEqual(config.returncode, 0, "Compose default configuration failed")
        default_ports = [
            (name, port.get("host_ip"), str(port.get("published")))
            for name, service in json.loads(config.stdout)["services"].items()
            for port in service.get("ports", [])
        ]
        self.assertEqual(default_ports, [("nginx", "127.0.0.1", "8080")])
        checks = http.Acceptance()
        fixtures = [f"person{index}@example.test" for index in range(1, 6)]
        ids = []
        last_challenge = None
        for fixture in fixtures:
            payload = {"channel": "EMAIL", "destination": fixture}
            result = http.call("POST", "/auth/challenges", payload)
            if result[0] == 429:
                _, headers = checks.response(result, 429, "RATE_LIMITED")
                delay = int(headers["Retry-After"])
                self.assertGreaterEqual(delay, 0)
                self.assertLessEqual(delay, 60)
                time.sleep(delay + 1)
                result = http.call("POST", "/auth/challenges", payload)
            last_challenge, _ = checks.response(result, 201)
            session, _ = checks.response(checks.verify(last_challenge), 200)
            self.assertIs(session["profileComplete"], True)
            ids.append(session["userId"])
        self.assertEqual(len(set(ids)), 5)
        self.compose_ok("up", "--build", "-d", "--wait")
        self.compose_ok("restart", "identity")
        for service in APPS:
            self.wait_ready(service, 200)
        checks.wait_for_resend(last_challenge)
        for fixture, previous_id in zip(fixtures, ids):
            session = checks.signin("EMAIL", fixture)
            self.assertIs(session["profileComplete"], True)
            self.assertTrue(session["userId"] == previous_id, "seeded account ID changed")

    def test_ac06_databases_and_session_state(self):
        checks = http.Acceptance()
        token = checks.signin("EMAIL", os.environ["D00_FAILURE_EMAIL"])["accessToken"]
        checks.assert_admitted(token)
        profile, _ = checks.response(http.call("GET", "/me", token=token), 200)
        for service in APPS:
            with self.subTest(database=service):
                db = f"{service}-db"
                try:
                    self.compose_ok("stop", db)
                    body = self.wait_ready(service, 503)
                    self.assertEqual(json.loads(body), {"status": "error", "reason": "db"})
                    for other in set(APPS) - {service}:
                        self.wait_ready(other, 200)
                finally:
                    self.compose_ok("start", db)
                    self.wait_ready(service, 200)
        after, _ = checks.response(http.call("GET", "/me", token=token), 200)
        self.assertTrue(after == profile, "profile changed after database recovery")
        try:
            self.compose_ok("stop", "redis")
            for method, path in http.GATES:
                status, body, _ = http.call(method, path, token=token)
                self.assertIn(status, {401, 403, 503}, path)
                self.assertNotRegex(json.dumps(body), re.compile(r"(postgres(?:ql)?|redis)://"))
        finally:
            self.compose_ok("start", "redis")
            for service in APPS:
                self.wait_ready(service, 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
