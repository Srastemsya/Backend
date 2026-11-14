#!/usr/bin/env python3
"""Capture user ids of dev participants 1-5 on a pre-upgrade stand.

Black-box helper: talks to the public HTTP API via Nginx only. Writes a JSON
artifact that be_l01_acceptance.py compares after the upgrade. Run it once
against the previous build before starting the BE-L01 build on the same
Compose volumes.

Usage: be_l01_prev_capture.py <base-url> <output.json>
"""
import json
import sys
import time
import urllib.error
import urllib.request
import uuid

OTP = "0427"


def request(base, path, method="GET", body=None, token=None, headers=None):
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
    req = urllib.request.Request(base + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        return exc.code, (json.loads(raw) if raw else None)


def login(base, email):
    deadline = time.time() + 150
    while True:
        status, payload = request(
            base, "/v1/auth/challenges", "POST",
            {"channel": "EMAIL", "destination": email},
        )
        if status == 429:
            retry = 61
            remaining = deadline - time.time()
            if remaining <= 0:
                raise SystemExit("rate limited for %s" % email)
            time.sleep(min(retry, remaining))
            continue
        if status != 201:
            raise SystemExit("challenge %s -> %s %s" % (email, status, payload))
        break
    status, session = request(
        base, "/v1/auth/challenges/%s/verify" % payload["challengeId"], "POST",
        {"code": OTP},
    )
    if status != 200:
        raise SystemExit("verify %s -> %s %s" % (email, status, session))
    return session


def main():
    base = sys.argv[1].rstrip("/")
    output = sys.argv[2]
    result = {}
    for number in range(1, 6):
        email = "person%d@example.test" % number
        session = login(base, email)
        status, profile = request(base, "/v1/me", token=session["accessToken"])
        if status != 200:
            raise SystemExit("profile %s -> %s" % (email, status))
        result[email] = {
            "userId": session["userId"],
            "profileId": profile.get("id"),
            "profileComplete": profile.get("profileComplete"),
        }
    with open(output, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    print(output)


if __name__ == "__main__":
    main()
