"""SR-1, SR-6: a patient cannot read another patient's record."""

from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from test_harness import TestRun, http, login  # noqa: E402

BASE = os.environ["APP_BASE_URL"]


def _find_patient_ids_as_admin() -> dict[str, str | None]:
    """Use admin session to look up patient ids by medical_record_number."""
    s, _ = login(BASE, os.environ["ADMIN_USERNAME"], os.environ["ADMIN_PASSWORD"])
    if s is None:
        return {"a": None, "b": None}
    r, _ = http(s, "GET", f"{BASE}/api/patients/")
    if r is None or r.status_code != 200:
        return {"a": None, "b": None}
    try:
        rows = r.json()
        if isinstance(rows, dict):
            rows = rows.get("results", [])
    except Exception:
        rows = []
    out = {"a": None, "b": None}
    for row in rows:
        mrn = row.get("medical_record_number", "")
        if mrn == "MRN-PATA":
            out["a"] = row.get("id")
        elif mrn == "MRN-PATB":
            out["b"] = row.get("id")
    return out


def _ensure_appointment_for_b(patient_b_id: str) -> str | None:
    """Create an appointment for patient B as admin, so there's data that
    patient A might leak. Returns the appointment id (or None on failure)."""
    s, _ = login(BASE, os.environ["ADMIN_USERNAME"], os.environ["ADMIN_PASSWORD"])
    if s is None:
        return None
    start = dt.datetime.combine(dt.date.today() + dt.timedelta(days=2), dt.time(9, 0))
    body = {
        "patient": patient_b_id,
        "scheduled_start": start.isoformat() + "Z",
        "scheduled_end": (start + dt.timedelta(minutes=30)).isoformat() + "Z",
        "reason": "SR-1 cross-tenant test",
        "status": "requested",
    }
    r, _ = http(s, "POST", f"{BASE}/api/appointments/", json=body)
    if r is not None and r.status_code in (200, 201):
        try:
            return r.json().get("id")
        except Exception:
            return None
    return None


def run():
    results = []

    # ---- Sub-test 1: cross-patient detail GET --------------------------------
    t = TestRun("test_sr01_cross_patient_detail", ["SR-1", "SR-6"],
                "Cross-patient access denied (detail GET)")
    ids = _find_patient_ids_as_admin()
    if not (ids["a"] and ids["b"]):
        results.append(t.to_skip(
            "Could not resolve patient ids via admin (admin login failed or no rows)."
        ))
        return _add_appointment_test(results)

    sess_a, login_step = login(BASE, os.environ["PATIENT_A_USERNAME"], os.environ["PATIENT_A_PASSWORD"])
    t.add(login_step)
    if sess_a is None:
        results.append(t.to_fail(
            "Method: log in as patient A.\n"
            "Expected: 200 with auth cookies.\n"
            f"Observed: login failed (no session)."
        ))
        return _add_appointment_test(results)

    target_url = f"{BASE}/api/patients/{ids['b']}/"
    r, step = http(sess_a, "GET", target_url)
    t.add(step)
    status = r.status_code if r is not None else None
    body_snippet = (r.text[:200] if r is not None else "(no response)")
    if status in (403, 404):
        results.append(t.to_pass(
            f"Method: as patient A, GET /api/patients/{{B_id}}/.\n"
            f"Expected: HTTP 403 or 404.\n"
            f"Observed: HTTP {status}.",
            notes=f"Body snippet: {body_snippet!r}",
        ))
    else:
        results.append(t.to_fail(
            f"Method: as patient A, GET /api/patients/{{B_id}}/.\n"
            f"Expected: HTTP 403 or 404.\n"
            f"Observed: HTTP {status} (body: {body_snippet!r})."
        ))

    return _add_appointment_test(results, ids)


def _add_appointment_test(results, ids=None):
    t2 = TestRun("test_sr01_no_other_appointments", ["SR-1", "SR-6"],
                 "Patient A's appointment list excludes patient B's rows")

    if ids is None or not ids.get("b"):
        results.append(t2.to_skip("Could not resolve patient B id."))
        return results

    appt_id = _ensure_appointment_for_b(ids["b"])
    sess_a, login_step = login(BASE, os.environ["PATIENT_A_USERNAME"], os.environ["PATIENT_A_PASSWORD"])
    t2.add(login_step)
    if sess_a is None:
        results.append(t2.to_fail(
            "Method: log in as patient A. Expected 200. Observed: login failed."
        ))
        return results

    r, step = http(sess_a, "GET", f"{BASE}/api/appointments/")
    t2.add(step)
    if r is None or r.status_code != 200:
        results.append(t2.to_fail(
            f"Method: as patient A, GET /api/appointments/.\n"
            f"Expected: HTTP 200 with own rows only.\n"
            f"Observed: HTTP {r.status_code if r is not None else 'no response'}."
        ))
        return results

    try:
        rows = r.json()
        if isinstance(rows, dict):
            rows = rows.get("results", rows)
    except Exception:
        rows = []
    leaked = [row for row in rows if str(row.get("patient")) == str(ids["b"])]
    if leaked:
        results.append(t2.to_fail(
            f"Method: as patient A, GET /api/appointments/.\n"
            f"Expected: zero rows belonging to patient B.\n"
            f"Observed: {len(leaked)} leaked row(s) referencing patient B."
        ))
    else:
        results.append(t2.to_pass(
            f"Method: as patient A, GET /api/appointments/ (after creating one for B).\n"
            f"Expected: zero rows belonging to patient B.\n"
            f"Observed: {len(rows)} appointment(s) returned, none belonging to patient B."
            + (f" (B's appointment id: {appt_id})" if appt_id else "")
        ))
    return results
