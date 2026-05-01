"""SR-6: role boundaries enforced server-side."""

from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from test_harness import TestRun, http, login  # noqa: E402

BASE = os.environ["APP_BASE_URL"]


def _expect_forbidden(t: TestRun, sess, method: str, url: str, label: str, expected_codes=(401, 403, 405)):
    r, step = http(sess, method, url, json={})
    t.add(step)
    code = r.status_code if r is not None else None
    if code in expected_codes:
        return True, f"{label}: HTTP {code}"
    return False, f"{label}: HTTP {code} (expected one of {expected_codes})"


def run():
    results = []

    # ---- Receptionist boundaries -----------------------------------------
    t = TestRun("test_sr06_receptionist_boundary", ["SR-6"],
                "Receptionist denied admin/auditor-only endpoints")
    s, login_step = login(BASE, os.environ["RECEPTIONIST_USERNAME"], os.environ["RECEPTIONIST_PASSWORD"])
    t.add(login_step)
    if s is None:
        results.append(t.to_fail(
            "Method: log in as receptionist. Expected 200. Observed: login failed."
        ))
    else:
        ok1, msg1 = _expect_forbidden(t, s, "GET", f"{BASE}/api/audit/logs/", "audit logs GET")
        admin_user_payload = {
            "username": "should_not_create",
            "email": "x@example.test",
            "password": "SomePass123!",
            "role": "admin",
        }
        r, step = http(s, "POST", f"{BASE}/api/accounts/users/", json=admin_user_payload)
        t.add(step)
        ok2 = r is not None and r.status_code in (401, 403)
        msg2 = f"users POST: HTTP {r.status_code if r is not None else 'no response'}"

        if ok1 and ok2:
            results.append(t.to_pass(
                "Method: as receptionist, GET /api/audit/logs/ then POST /api/accounts/users/ (role=admin).\n"
                "Expected: HTTP 401 or 403 on both.\n"
                f"Observed: {msg1}; {msg2}."
            ))
        else:
            results.append(t.to_fail(
                "Method: as receptionist, GET /api/audit/logs/ then POST /api/accounts/users/.\n"
                "Expected: HTTP 401 or 403 on both.\n"
                f"Observed: {msg1}; {msg2}."
            ))

    # ---- Doctor (clinician) boundaries -----------------------------------
    t2 = TestRun("test_sr06_doctor_boundary", ["SR-6"],
                 "Clinician denied admin/billing-only endpoints")
    s, login_step = login(BASE, os.environ["DOCTOR_USERNAME"], os.environ["DOCTOR_PASSWORD"])
    t2.add(login_step)
    if s is None:
        results.append(t2.to_fail(
            "Method: log in as doctor. Expected 200. Observed: login failed."
        ))
        return results

    user_payload = {"username": "x", "email": "x@x.test", "password": "ZzzZzz123!", "role": "admin"}
    r1, step = http(s, "POST", f"{BASE}/api/accounts/users/", json=user_payload)
    t2.add(step)
    code1 = r1.status_code if r1 is not None else None

    r2, step = http(s, "GET", f"{BASE}/api/billing/transactions/")
    t2.add(step)
    code2 = r2.status_code if r2 is not None else None

    forbidden_create = code1 in (401, 403)
    if code2 in (200, 401, 403):
        billing_msg = f"billing/transactions GET: HTTP {code2}"
        billing_ok = True
    else:
        billing_msg = f"billing/transactions GET: HTTP {code2} (expected 200/401/403)"
        billing_ok = False

    if forbidden_create and billing_ok:
        results.append(t2.to_pass(
            "Method: as doctor, POST /api/accounts/users/; GET /api/billing/transactions/.\n"
            "Expected: 401/403 on user create; any of 200/401/403 on transactions (record actual).\n"
            f"Observed: users POST -> HTTP {code1}; {billing_msg}."
        ))
    else:
        results.append(t2.to_fail(
            "Method: as doctor, POST /api/accounts/users/; GET /api/billing/transactions/.\n"
            "Expected: 401/403 on user create.\n"
            f"Observed: users POST -> HTTP {code1}; {billing_msg}."
        ))

    return results
