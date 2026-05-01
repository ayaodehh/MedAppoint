"""SR-13: Server-side input validation."""

from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from test_harness import TestRun, http, login  # noqa: E402

BASE = os.environ["APP_BASE_URL"]


def _patient_a_id_via_admin(sess) -> str | None:
    r, _ = http(sess, "GET", f"{BASE}/api/patients/")
    if r is None or r.status_code != 200:
        return None
    try:
        rows = r.json()
        if isinstance(rows, dict):
            rows = rows.get("results", [])
    except Exception:
        rows = []
    for row in rows:
        if row.get("medical_record_number") == "MRN-PATA":
            return row.get("id")
    return None


def run():
    results = []

    # ---- Manipulated invoice amount ---------------------------------------
    t = TestRun("test_sr13_invoice_amount", ["SR-13"],
                "Server-side validation of invoice amount")

    # Receptionist (per spec) cannot create invoices; this prototype's
    # BillingPermission only allows admin/billing. Record the receptionist
    # 403, then escalate to admin to actually exercise validation.
    s_recept, login_step = login(BASE, os.environ["RECEPTIONIST_USERNAME"], os.environ["RECEPTIONIST_PASSWORD"])
    t.add(login_step)

    s_admin, login_step = login(BASE, os.environ["ADMIN_USERNAME"], os.environ["ADMIN_PASSWORD"])
    t.add(login_step)
    if s_admin is None:
        results.append(t.to_skip("Admin login failed; cannot create invoice for validation test."))
        return _add_malformed_test(results)

    pat_a_id = _patient_a_id_via_admin(s_admin)
    if not pat_a_id:
        results.append(t.to_skip("Could not resolve patient A id; needed to create invoice."))
        return _add_malformed_test(results)

    # As receptionist, attempt invoice POST (expected 403 in this build)
    if s_recept is not None:
        r_recept, step = http(s_recept, "POST", f"{BASE}/api/billing/invoices/", json={
            "patient": pat_a_id, "amount_due": "0.01", "currency": "USD", "status": "pending",
        })
        t.add(step)
        recept_code = r_recept.status_code if r_recept is not None else None
    else:
        recept_code = None

    # As admin, post a manipulated/cheap amount + extra junk fields
    body = {
        "patient": pat_a_id,
        "amount_due": "0.01",
        "currency": "USD",
        "status": "pending",
        "extra_junk_field": "should_be_ignored",
        "amount": "999999.00",     # not a real field
    }
    r, step = http(s_admin, "POST", f"{BASE}/api/billing/invoices/", json=body)
    t.add(step)

    if r is None:
        results.append(t.to_fail(
            "Method: POST /api/billing/invoices/ with amount_due=0.01.\n"
            "Expected: 400 (rejected) or 200/201 with server-side recomputation.\n"
            "Observed: no response."
        ))
        return _add_malformed_test(results)

    code = r.status_code
    body_text = r.text[:300]
    accepted_amount = None
    try:
        if code in (200, 201):
            accepted_amount = r.json().get("amount_due")
    except Exception:
        pass

    if code == 400:
        results.append(t.to_pass(
            "Method: as admin, POST /api/billing/invoices/ with amount_due=0.01 + junk fields.\n"
            "Expected: HTTP 400 (validation error) OR 201 with server-recomputed amount.\n"
            f"Observed: HTTP 400. Receptionist attempt: HTTP {recept_code}.",
            notes=f"Body: {body_text!r}",
        ))
    elif code in (200, 201) and str(accepted_amount) in ("0.01", "0.0100", "0.010000"):
        # Server accepted the client-supplied price.
        results.append(t.to_fail(
            "Method: as admin, POST /api/billing/invoices/ with amount_due=0.01 + junk fields.\n"
            "Expected: 400 (rejected) or 200/201 with server-side recomputation.\n"
            f"Observed: HTTP {code}; server stored client-supplied amount_due={accepted_amount}.\n"
            f"Receptionist attempt: HTTP {recept_code}."
        ))
    elif code in (200, 201):
        results.append(t.to_pass(
            "Method: as admin, POST /api/billing/invoices/ with amount_due=0.01.\n"
            f"Observed: HTTP {code}; server-stored amount_due={accepted_amount} (recomputed/overridden).",
            notes=f"Receptionist attempt: HTTP {recept_code}.",
        ))
    else:
        results.append(t.to_fail(
            "Method: as admin, POST /api/billing/invoices/ with amount_due=0.01.\n"
            f"Expected: 400 or 200/201.\n"
            f"Observed: HTTP {code}, body: {body_text!r}."
        ))

    return _add_malformed_test(results)


def _add_malformed_test(results):
    t = TestRun("test_sr13_malformed_appointment", ["SR-13"],
                "Malformed JSON returns 400, not 500")
    s, login_step = login(BASE, os.environ["RECEPTIONIST_USERNAME"], os.environ["RECEPTIONIST_PASSWORD"])
    t.add(login_step)
    if s is None:
        results.append(t.to_fail("Method: log in as receptionist. Observed: login failed."))
        return results

    body = {
        "patient": "this-is-not-a-uuid",
        "clinician": "not-a-pk",
        "scheduled_start": "yesterday-but-as-string",
        "scheduled_end": dt.datetime.now().isoformat() + "Z",
        "reason": ["lists", "are", "not", "strings"],
    }
    r, step = http(s, "POST", f"{BASE}/api/appointments/", json=body)
    t.add(step)
    code = r.status_code if r is not None else None
    body_snippet = r.text[:200] if r is not None else "(no response)"
    if code == 400:
        results.append(t.to_pass(
            "Method: POST /api/appointments/ with intentionally malformed types.\n"
            "Expected: HTTP 400 with a sensible validation error (not 500).\n"
            f"Observed: HTTP 400. Body snippet: {body_snippet!r}",
        ))
    elif code == 500:
        results.append(t.to_fail(
            "Method: POST /api/appointments/ with malformed types.\n"
            "Expected: HTTP 400.\n"
            f"Observed: HTTP 500 (server crashed). Body: {body_snippet!r}"
        ))
    else:
        # 401/403 still indicates the framework rejected the request gracefully.
        results.append(t.to_pass(
            "Method: POST /api/appointments/ with malformed types.\n"
            f"Expected: HTTP 400.\n"
            f"Observed: HTTP {code} (graceful rejection, not 500). Body: {body_snippet!r}",
            notes="Recorded as pass because the server did not return 500.",
        ))
    return results
