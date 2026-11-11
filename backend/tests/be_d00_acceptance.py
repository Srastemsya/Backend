"""BE-D00 acceptance against the public gateway and documented dev fixtures."""
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
import os
import threading
import time
import unittest
import urllib.error
import urllib.request
import uuid


BASE = os.getenv("D00_URL", "http://127.0.0.1:8080") + "/v1"
CODE = os.getenv("D00_OTP", "0427")
GATES = (("GET", "/home"), ("GET", "/rooms"))


def call(method, path, payload=None, token=None, key=None):
    headers = {}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    if method == "POST":
        headers["Idempotency-Key"] = key or str(uuid.uuid4())
    request = urllib.request.Request(
        BASE + path,
        json.dumps(payload).encode() if payload is not None else None,
        headers,
        method=method,
    )
    try:
        response = urllib.request.urlopen(request, timeout=10)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        raw = response.read()
        try:
            data = json.loads(raw) if raw else {}
        except ValueError:
            data = {}
        return response.status, data, response.headers


class Acceptance(unittest.TestCase):
    def response(self, result, status, code=None):
        actual, data, headers = result
        self.assertEqual(actual, status)
        if code:
            self.assertEqual(data.get("error", {}).get("code"), code)
            self.assertTrue(data["error"].get("requestId"))
        return data, headers

    def challenge(self, channel, contact):
        data, _ = self.response(call("POST", "/auth/challenges", {
            "channel": channel, "destination": contact,
        }), 201)
        self.assertEqual(set(data), {"challengeId", "expiresAt", "resendAvailableAt"})
        return data

    def verify(self, challenge, code=CODE, key=None):
        return call("POST", "/auth/challenges/" + challenge["challengeId"] + "/verify",
                    {"code": code}, key=key)

    def wait_for_resend(self, challenge):
        available_at = datetime.fromisoformat(challenge["resendAvailableAt"].replace("Z", "+00:00"))
        delay = available_at.timestamp() - time.time()
        self.assertLessEqual(delay, 61)
        time.sleep(max(0, delay) + 0.35)

    def signin(self, channel, destination):
        session, _ = self.response(self.verify(self.challenge(channel, destination)), 200)
        self.assertTrue({"accessToken", "accessExpiresAt", "refreshToken", "refreshExpiresAt",
                         "userId", "profileComplete"}.issubset(session))
        return session

    def check_rejection(self, scenario, token=None):
        expected_codes = {"UNAUTHENTICATED"}
        if token:
            expected_codes.add("SESSION_EXPIRED")
        failures = []
        for method, path in GATES:
            status, data, _ = call(method, path, token=token)
            code = data.get("error", {}).get("code")
            if status != 401 or code not in expected_codes:
                observed = code if code in expected_codes | {"UNAUTHORIZED", "FORBIDDEN"} else "other"
                failures.append(f"{scenario} {path}: {status} {observed}")
        return failures

    def test_ac01_unauthenticated_gates(self):
        failures = self.check_rejection("missing token")
        self.assertFalse(failures, "D00 sanitized failure: " + ", ".join(failures))

    def assert_admitted(self, token):
        for method, path in GATES:
            status, _, _ = call(method, path, token=token)
            self.assertEqual(status, 200, path)

    def test_ac01_phone_email_registration_and_relogin(self):
        self.assertRegex(CODE, r"^0[0-9]{3}$")
        sms = self.signin("SMS", os.environ["D00_SMS"])
        self.assertTrue(sms["userId"])
        email = os.environ["D00_NEW_EMAIL"]
        challenge = self.challenge("EMAIL", email)
        session, _ = self.response(self.verify(challenge), 200)
        self.assertIs(session["profileComplete"], False)
        token = session["accessToken"]
        for method, path in GATES:
            self.response(call(method, path, token=token), 403, "PROFILE_INCOMPLETE")
        self.response(call("PUT", "/me/registration", {
            "displayName": " ", "birthDate": "1994-10-10",
        }, token=token), 422, "VALIDATION_ERROR")
        registration = {"displayName": "Acceptance Test", "birthDate": "1994-10-10"}
        profile, _ = self.response(call("PUT", "/me/registration", registration, token=token), 200)
        self.assertIs(profile["profileComplete"], True)
        self.assertTrue(profile["id"] == session["userId"])
        self.assert_admitted(token)
        self.wait_for_resend(challenge)
        normalized_contact = " " + email.upper() + " "
        again = self.signin("EMAIL", normalized_contact)
        self.assertTrue(again["userId"] == session["userId"])
        self.assertIs(again["profileComplete"], True)
        profile, _ = self.response(call("GET", "/me", token=again["accessToken"]), 200)
        for field, expected in registration.items():
            self.assertEqual(profile[field], expected)

    def test_ac02_challenge_errors_and_concurrency(self):
        contact = os.environ["D00_RACE_EMAIL"]
        old = self.challenge("EMAIL", contact)
        self.response(self.verify(old, "0000" if CODE != "0000" else "9999"), 422, "OTP_INVALID")
        _, headers = self.response(call("POST", "/auth/challenges", {
            "channel": "EMAIL", "destination": contact,
        }), 429, "RATE_LIMITED")
        self.assertTrue((headers.get("Retry-After") or "").isdigit())
        self.wait_for_resend(old)
        new = self.challenge("EMAIL", contact)
        self.assertTrue(old["challengeId"] != new["challengeId"])
        self.response(self.verify(old), 410, "OTP_EXPIRED")
        barrier = threading.Barrier(2)

        def verify(key):
            barrier.wait(timeout=5)
            return self.verify(new, key=key)

        keys = [str(uuid.uuid4()), str(uuid.uuid4())]
        with ThreadPoolExecutor(2) as executor:
            results = list(executor.map(verify, keys))
        self.assertEqual(sorted(result[0] for result in results), [200, 410])
        winner = next(index for index, result in enumerate(results) if result[0] == 200)
        replay, _ = self.response(self.verify(new, key=keys[winner]), 200)
        self.assertTrue(replay == results[winner][1], "verify replay changed the session")

    def test_ac03_refresh_reuse_forgery_and_logout(self):
        session = self.signin("EMAIL", os.environ["D00_REFRESH_EMAIL"])
        token = session["accessToken"]
        self.assert_admitted(token)
        header, payload, signature = token.split(".")
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        self.assertTrue({"iss", "aud", "sub", "sid", "iat", "exp"}.issubset(claims))
        self.assertEqual(claims["exp"] - claims["iat"], 900)
        forged_signature = ("A" if signature[0] != "A" else "B") + signature[1:]
        failures = self.check_rejection("invalid signature", ".".join((header, payload, forged_signature)))
        original = {"refreshToken": session["refreshToken"]}
        key = str(uuid.uuid4())
        rotated, _ = self.response(call("POST", "/auth/refresh", original, key=key), 200)
        replay, _ = self.response(call("POST", "/auth/refresh", original, key=key), 200)
        self.assertTrue(rotated == replay, "refresh replay changed the session")
        self.assertTrue(rotated["refreshToken"] != session["refreshToken"])
        self.assert_admitted(rotated["accessToken"])
        self.response(call("POST", "/auth/refresh", original), 401)
        failures.extend(self.check_rejection("family revoked", rotated["accessToken"]))
        self.response(call("POST", "/auth/refresh", {"refreshToken": rotated["refreshToken"]}), 401)
        logout = self.signin("EMAIL", os.environ["D00_LOGOUT_EMAIL"])
        self.assert_admitted(logout["accessToken"])
        self.response(call("DELETE", "/auth/session", token=logout["accessToken"]), 204)
        failures.extend(self.check_rejection("logged out", logout["accessToken"]))
        self.response(call("POST", "/auth/refresh", {"refreshToken": logout["refreshToken"]}), 401)
        self.assertFalse(failures, "D00 sanitized failure: " + ", ".join(failures))


if __name__ == "__main__":
    unittest.main(verbosity=2)
