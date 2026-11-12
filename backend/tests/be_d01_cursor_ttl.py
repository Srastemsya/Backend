"""Observe expiration of both public catalog cursors."""
import os
from pathlib import Path
import time
import unittest

import be_d01_acceptance as acceptance


class CursorLifetime(unittest.TestCase):
    def test_ac03_cursor_expires_after_thirty_minutes(self):
        client = acceptance.Discovery()
        session = client.login("person5@example.test")
        token = session["accessToken"]
        filters = {"kind": "EVENT", "categoryId": "outdoors"}
        queries = (("/catalog/search", filters),
                   ("/catalog/map", {**filters, "bbox": "131.87,43.10,131.91,43.13"}))
        cursors = []
        start = time.time()
        for path, query in queries:
            cursor = client.request(path, token=token, query=query)["nextCursor"]
            self.assertTrue(cursor, "Expiry fixture must supply over 20 matches")
            cursors.append((path, {**query, "cursor": cursor}))
        ready = time.time()

        def wait_until(deadline):
            while time.time() < deadline:
                time.sleep(min(5, max(0, deadline - time.time())))

        def refresh(current):
            return client.request("/auth/refresh", method="POST",
                                  body={"refreshToken": current["refreshToken"]})

        def confirm_active():
            for path, query in cursors:
                self.assertTrue(client.request(path, token=token, query=query)["items"])

        control = os.environ.get("D01_TTL_CONTROL_DIR")
        if control:
            confirm_active()
            control_path = Path(control)
            cursor_file = control_path / "cursor-values"
            with os.fdopen(
                os.open(cursor_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w"
            ) as output:
                for _, query in cursors:
                    output.write(query["cursor"] + "\n")
            (control_path / "cursors-issued").touch()
            deadline = time.time() + 180
            while not (control_path / "cursors-expired").exists():
                self.assertLess(time.time(), deadline, "Controlled expiry fixture timed out")
                time.sleep(1)
        else:
            wait_until(start + 12 * 60)
            session = refresh(session)
            wait_until(start + 24 * 60)
            session = refresh(session)
            token = session["accessToken"]

            wait_until(start + 30 * 60 - 10)
            self.assertLess(time.time(), start + 30 * 60 - 2,
                            "Host suspension crossed the pre-expiration observation window")
            confirm_active()
            wait_until(ready + 30 * 60 + 10)

        for path, query in cursors:
            client.assert_error(path, 409, "CURSOR_EXPIRED", token, query)


if __name__ == "__main__":
    unittest.main(verbosity=2)
