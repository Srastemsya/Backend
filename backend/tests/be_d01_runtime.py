"""External Compose and readiness checks for the isolated D01 test project."""
import json
import os
from pathlib import Path
import subprocess
import time
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import be_d01_acceptance as acceptance

BACKEND = Path(__file__).resolve().parents[1]
PROJECT = os.environ.get("D01_PROJECT", "srastemsya-be-d01-tester")
COMPOSE = ["docker", "compose", "-p", PROJECT, "-f", "compose.yaml", "-f", "compose.dev.yaml"]


def run(args):
    return subprocess.run(args, cwd=BACKEND, capture_output=True, text=True, check=True).stdout


def compose(*args):
    return run([*COMPOSE, *args])


def health(path):
    try:
        response = urlopen(acceptance.BASE + path, timeout=5)
    except HTTPError as error:
        response = error
    with response:
        return response.code, response.read().decode()


class Runtime(unittest.TestCase):
    def test_ac05_repeat_compose_and_published_ports(self):
        client = acceptance.Discovery()
        client.owner = client.login("person4@example.test")
        paths = ("/home", "/catalog/categories", "/catalog/search", "/catalog/EVENT/dev-vlad-workshop")
        def read_public_data():
            results = [client.get(path) for path in paths]
            results[2].pop("nextCursor")
            return results

        before = read_public_data()
        output = compose("ps", "--format", "json")
        containers = (json.loads(output) if output.lstrip().startswith("[")
                      else [json.loads(line) for line in output.splitlines()])
        published = {item["Service"] for item in containers
                     if any(port.get("PublishedPort") for port in (item.get("Publishers") or []))}
        self.assertEqual(published, {"nginx"})
        compose("up", "--build", "-d", "--wait")
        for path in ("/identity/health", "/catalog/health", "/swipes/health"):
            self.assertEqual(health(path)[0], 200, path)
        self.assertEqual(before, read_public_data())
        for entries in (before[0]["quickCategories"], before[0]["collections"], before[1]["items"]):
            identifiers = [entry["id"] for entry in entries]
            self.assertEqual(len(identifiers), len(set(identifiers)))
        for entries in (before[0]["upcoming"], before[2]["items"]):
            refs = [(entry["ref"]["kind"], entry["ref"]["id"]) for entry in entries]
            self.assertEqual(len(refs), len(set(refs)))

    def test_ac06_catalog_database_outage_and_recovery(self):
        self.assertTrue(PROJECT.endswith("-tester"), "Use only a dedicated tester project")
        database_id = compose("ps", "-q", "catalog-db").strip()
        db_env = json.loads(run(["docker", "inspect", "--format", "{{json .Config.Env}}", database_id]))
        credentials = dict(entry.split("=", 1) for entry in db_env)
        password = credentials["POSTGRES_PASSWORD"]
        secrets = [password, credentials["POSTGRES_USER"]]
        self.assertTrue(all(secrets))
        start = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.assertEqual(health("/catalog/health")[0], 200)
        try:
            compose("stop", "catalog-db")
            status, body = health("/catalog/health")
            self.assertEqual(status, 503)
            self.assertEqual(health("/identity/health")[0], 200)
            self.assertEqual(health("/swipes/health")[0], 200)
        finally:
            compose("start", "catalog-db")
        recovered = 0
        for _ in range(30):
            try:
                recovered, _ = health("/catalog/health")
            except URLError:
                recovered = 0
            if recovered == 200:
                break
            time.sleep(1)
        self.assertEqual(recovered, 200)
        logs = compose("logs", "--since", start, "catalog", "nginx", "catalog-db")
        self.assertFalse(any(secret in body for secret in secrets), "Credential leaked in response")
        # PostgreSQL usernames can equal a service or program name. Inspect catalog's
        # application logs for the credential values and URL-style credentials.
        catalog_logs = compose("logs", "--since", start, "catalog")
        self.assertFalse(any(secret in catalog_logs for secret in secrets), "Credential leaked in catalog logs")
        self.assertFalse(password in logs, "Password leaked in runtime logs")


if __name__ == "__main__":
    unittest.main(verbosity=2)
