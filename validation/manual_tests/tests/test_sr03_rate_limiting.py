"""SR-3: auth endpoints reject brute-force attempts."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from test_harness import TestRun, capture, django_manage  # noqa: E402

BASE = os.environ["APP_BASE_URL"]
# Use an existing user so axes counts the failures (axes' default
# behaviour requires a real authenticate() call to fire the failed-login
# signal). Cleanup at the end resets the lockout so subsequent tests can
# log in as this user normally.
TARGET = os.environ["PATIENT_B_USERNAME"]
TARGET_CORRECT = os.environ["PATIENT_B_PASSWORD"]
ATTEMPTS = 15


def run():
    t = TestRun("test_sr03_rate_limiting", ["SR-3"],
                "Rate limiting / lockout on auth endpoints")
    s = requests.Session()
    statuses: list[int | None] = []
    timings: list[float] = []

    for i in range(ATTEMPTS):
        t0 = time.time()
        try:
            r = s.post(
                f"{BASE}/api/auth/login/",
                json={"username": TARGET, "password": f"definitely_wrong_{i}"},
                timeout=10,
            )
            elapsed = time.time() - t0
            statuses.append(r.status_code)
            timings.append(elapsed)
            if i in (0, 4, 5, 14):
                t.add(capture("POST", f"{BASE}/api/auth/login/", r,
                              {"json": {"username": TARGET, "password": f"definitely_wrong_{i}"}}))
        except requests.RequestException:
            statuses.append(None)
            timings.append(time.time() - t0)

    # Conclusive lockout proof: the correct password should now be rejected.
    correct_code: int | None = None
    correct_cookie_set = False
    try:
        s2 = requests.Session()
        r_correct = s2.post(
            f"{BASE}/api/auth/login/",
            json={"username": TARGET, "password": TARGET_CORRECT},
            timeout=10,
        )
        correct_code = r_correct.status_code
        correct_cookie_set = "clinic_access_token" in (r_correct.headers.get("set-cookie") or "")
        t.add(capture("POST", f"{BASE}/api/auth/login/", r_correct,
                      {"json": {"username": TARGET, "password": "***correct***"}}))
    except requests.RequestException as exc:
        t.add({"request": {"method": "POST", "url": f"{BASE}/api/auth/login/", "headers": {}},
               "response": {"status": None, "headers": {}, "body": f"(transport error: {exc})"}})

    # Cleanup so this user can be used in later tests / future runs.
    try:
        django_manage("axes_reset_username", TARGET, timeout=30)
    except Exception:
        pass

    locked_403 = any(c == 403 for c in statuses)
    rate_limited = any(c == 429 for c in statuses)
    avg_early = sum(timings[:5]) / max(len(timings[:5]), 1)
    avg_late = sum(timings[5:]) / max(len(timings[5:]), 1)
    slowed = avg_late > avg_early * 1.5 and avg_late > 0.5
    correct_rejected = (correct_code is not None and correct_code != 200) or (correct_code == 200 and not correct_cookie_set)
    correct_accepted = correct_code == 200 and correct_cookie_set

    observed = (
        f"15 bad-password attempts: first 5 {statuses[:5]}, later 10 {statuses[5:]}; "
        f"correct-password follow-up -> HTTP {correct_code} (cookie set: {correct_cookie_set}); "
        f"avg early {avg_early*1000:.0f}ms, avg late {avg_late*1000:.0f}ms"
    )

    if correct_accepted and not (locked_403 or rate_limited or slowed):
        # Lockout did not engage at all - rate limiting isn't working.
        return [t.to_fail(
            "Method: 15 bad-password attempts then correct password.\n"
            "Expected: 429 / 403 / lockout (correct password rejected) / observable slowdown.\n"
            f"Observed: none. {observed}."
        )]

    if correct_rejected or locked_403 or rate_limited or slowed:
        return [t.to_pass(
            "Method: 15 bad-password attempts then a correct-password follow-up.\n"
            "Expected: at least one of {429, 403 lockout, slowdown, correct password rejected = lockout in effect}.\n"
            f"Observed: locked_403={locked_403}, rate_limited={rate_limited}, slowed={slowed}, "
            f"correct password rejected = {correct_rejected}. {observed}.",
            notes="django-axes wraps authenticate() so the lockout still surfaces as HTTP 400 "
                  "'Invalid credentials' (not 403), but a correct password being rejected proves "
                  "the lockout engaged.",
        )]

    return [t.to_fail(
        "Method: 15 bad-password attempts then correct-password follow-up.\n"
        "Expected: visible rate limit (429), axes 403, slowdown, or correct password rejected.\n"
        f"Observed: none of those. {observed}."
    )]
