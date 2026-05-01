"""SR-8: account lockout after repeated failures."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from test_harness import TestRun, capture, django_manage  # noqa: E402

BASE = os.environ["APP_BASE_URL"]
PATIENT = os.environ["PATIENT_A_USERNAME"]
PATIENT_PW = os.environ["PATIENT_A_PASSWORD"]


def run():
    t = TestRun("test_sr08_lockout", ["SR-8"], "Account locked after repeated failures")
    s = requests.Session()
    statuses: list[int | None] = []

    try:
        # 6 wrong-password attempts (axes default failure limit is 5)
        for i in range(6):
            try:
                r = s.post(
                    f"{BASE}/api/auth/login/",
                    json={"username": PATIENT, "password": "definitely_wrong"},
                    timeout=10,
                )
                statuses.append(r.status_code)
                if i in (0, 4, 5):
                    t.add(capture("POST", f"{BASE}/api/auth/login/", r,
                                  {"json": {"username": PATIENT, "password": "definitely_wrong"}}))
            except requests.RequestException:
                statuses.append(None)

        # Now try the CORRECT password
        try:
            r_correct = s.post(
                f"{BASE}/api/auth/login/",
                json={"username": PATIENT, "password": PATIENT_PW},
                timeout=10,
            )
            t.add(capture("POST", f"{BASE}/api/auth/login/", r_correct,
                          {"json": {"username": PATIENT, "password": "***correct***"}}))
            correct_code = r_correct.status_code
            correct_set_cookie = "clinic_access_token" in (r_correct.headers.get("set-cookie", "") or "")
        except requests.RequestException:
            correct_code = None
            correct_set_cookie = False

        locked = correct_code in (403, 401, 429) or (correct_code != 200 and not correct_set_cookie)
        if correct_code == 200 and correct_set_cookie:
            return [t.to_fail(
                "Method: 6 bad-password attempts then correct password.\n"
                "Expected: even correct password is denied (axes lockout).\n"
                f"Observed: bad-password statuses {statuses}; correct password -> HTTP {correct_code} "
                f"and a session cookie was issued."
            )]
        if locked:
            return [t.to_pass(
                "Method: 6 bad-password attempts then correct password.\n"
                "Expected: even correct password denied (axes lockout).\n"
                f"Observed: bad-password statuses {statuses}; correct password -> HTTP {correct_code} "
                f"and no session cookie issued.",
                notes="django-axes lockout engaged after 5 failures.",
            )]
        return [t.to_fail(
            "Method: 6 bad-password attempts then correct password.\n"
            f"Observed: bad statuses {statuses}; correct -> HTTP {correct_code}; cookie set: {correct_set_cookie}."
        )]
    finally:
        # Always reset axes for this user so subsequent runs can log in.
        try:
            res = django_manage("axes_reset_username", PATIENT, timeout=30)
            t.add({
                "request": {"method": "MANAGE", "url": "axes_reset_username " + PATIENT, "headers": {}},
                "response": {"status": res.returncode, "headers": {}, "body": (res.stdout or "") + (res.stderr or "")},
            })
        except Exception as exc:
            t.add({
                "request": {"method": "MANAGE", "url": "axes_reset_username " + PATIENT, "headers": {}},
                "response": {"status": -1, "headers": {}, "body": f"cleanup failed: {exc}"},
            })
