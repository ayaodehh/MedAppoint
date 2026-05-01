"""SR-12: Secure session management."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from test_harness import TestRun, capture, http, login  # noqa: E402

BASE = os.environ["APP_BASE_URL"]


def run():
    t = TestRun("test_sr12_session", ["SR-12"], "Secure session management (cookie flags + logout invalidation)")

    # Step 1: log in as patient A and inspect Set-Cookie
    s = requests.Session()
    try:
        login_response = s.post(
            f"{BASE}/api/auth/login/",
            json={"username": os.environ["PATIENT_A_USERNAME"], "password": os.environ["PATIENT_A_PASSWORD"]},
            timeout=10,
        )
    except requests.RequestException as exc:
        t.add({"request": {"method": "POST", "url": f"{BASE}/api/auth/login/", "headers": {}},
               "response": {"status": None, "headers": {}, "body": f"(transport error: {exc})"}})
        return [t.to_fail("Method: log in as patient A. Observed: transport error.")]

    raw_set_cookies = login_response.headers.get_all("Set-Cookie") if hasattr(login_response.headers, "get_all") \
        else (login_response.raw.headers.getlist("Set-Cookie") if hasattr(login_response.raw, "headers") else [])
    if not raw_set_cookies:
        # requests/urllib3 collapses duplicates; fall back to the single header.
        single = login_response.headers.get("set-cookie", "")
        raw_set_cookies = [single] if single else []

    t.add(capture("POST", f"{BASE}/api/auth/login/", login_response,
                  {"json": {"username": os.environ["PATIENT_A_USERNAME"], "password": "***"}}))

    if login_response.status_code != 200 or "clinic_access_token" not in s.cookies:
        return [t.to_fail(
            "Method: POST /api/auth/login/. Expected 200 with auth cookies.\n"
            f"Observed: HTTP {login_response.status_code}, cookies={list(s.cookies.keys())}."
        )]

    access_cookie_lines = [c for c in raw_set_cookies if "clinic_access_token=" in c]
    cookie_text = " ; ".join(access_cookie_lines).lower()
    httponly_set = "httponly" in cookie_text
    samesite_value = None
    for token in cookie_text.replace(" ", "").split(";"):
        if token.startswith("samesite="):
            samesite_value = token.split("=", 1)[1].rstrip(",").strip()
            break

    # Capture token value before logout for replay test
    captured_access_token = s.cookies.get("clinic_access_token")
    captured_refresh_token = s.cookies.get("clinic_refresh_token")

    # Step 4: logout
    r_logout, step = http(s, "POST", f"{BASE}/api/auth/logout/")
    t.add(step)

    # Step 5: replay the captured cookie in a fresh session
    s2 = requests.Session()
    if captured_access_token:
        s2.cookies.set("clinic_access_token", captured_access_token, domain="localhost", path="/")
    if captured_refresh_token:
        s2.cookies.set("clinic_refresh_token", captured_refresh_token, domain="localhost", path="/")
    r_replay, replay_step = http(s2, "GET", f"{BASE}/api/accounts/users/me/")
    t.add(replay_step)
    replay_status = r_replay.status_code if r_replay is not None else None
    replay_invalidated = replay_status in (401, 403)

    findings = []
    if not httponly_set:
        findings.append("HttpOnly missing on clinic_access_token")
    if not samesite_value:
        findings.append("SameSite missing on clinic_access_token")
    if not replay_invalidated:
        findings.append(f"replay after logout returned HTTP {replay_status} (expected 401)")

    summary = (
        "Method: log in as patient A; inspect Set-Cookie flags; logout; replay captured cookie in a new session against /api/accounts/users/me/.\n"
        f"Expected: HttpOnly set, SameSite set (Lax/Strict), replay returns HTTP 401.\n"
        f"Observed: HttpOnly={httponly_set}, SameSite={samesite_value!r}, "
        f"replay status={replay_status}."
    )

    if not findings:
        return [t.to_pass(summary, notes="All three checks passed.")]
    return [t.to_fail(summary + "\nFindings: " + "; ".join(findings))]
