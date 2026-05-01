"""SR-4, SR-5: audit log captures actions and is append-only."""

from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from test_harness import TestRun, django_shell, http, login  # noqa: E402

BASE = os.environ["APP_BASE_URL"]


def _patient_a_id() -> str | None:
    s, _ = login(BASE, os.environ["ADMIN_USERNAME"], os.environ["ADMIN_PASSWORD"])
    if s is None:
        return None
    r, _ = http(s, "GET", f"{BASE}/api/patients/")
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

    # ---- Audit log captures actions ---------------------------------------
    t = TestRun("test_sr04_audit_capture", ["SR-4"],
                "Audit log captures patient and admin actions")

    pat_a_id = _patient_a_id()
    if not pat_a_id:
        results.append(t.to_skip("Could not resolve patient A id via admin."))
        return _add_append_only(results)

    sess_a, step = login(BASE, os.environ["PATIENT_A_USERNAME"], os.environ["PATIENT_A_PASSWORD"])
    t.add(step)
    if sess_a is None:
        results.append(t.to_fail(
            "Method: log in as patient A. Expected 200. Observed: login failed."
        ))
        return _add_append_only(results)

    start = dt.datetime.combine(dt.date.today() + dt.timedelta(days=3), dt.time(11, 0))
    body = {
        "patient": pat_a_id,
        "scheduled_start": start.isoformat() + "Z",
        "scheduled_end": (start + dt.timedelta(minutes=30)).isoformat() + "Z",
        "reason": "SR-4 audit booking",
        "status": "requested",
    }
    r_book, step = http(sess_a, "POST", f"{BASE}/api/appointments/", json=body)
    t.add(step)
    appt_id = None
    if r_book is not None and r_book.status_code in (200, 201):
        try:
            appt_id = r_book.json().get("id")
        except Exception:
            appt_id = None

    # Patients cannot DELETE appointments (AppointmentPermission allows
    # destroy only for admin/receptionist), so cancel by PATCHing status.
    if appt_id is not None:
        r_cancel, step = http(sess_a, "PATCH", f"{BASE}/api/appointments/{appt_id}/",
                              json={"status": "cancelled"})
        t.add(step)

    sess_admin, step = login(BASE, os.environ["ADMIN_USERNAME"], os.environ["ADMIN_PASSWORD"])
    t.add(step)
    if sess_admin is None:
        results.append(t.to_fail(
            "Method: log in as admin. Expected 200. Observed: login failed."
        ))
        return _add_append_only(results)

    r_logs, step = http(sess_admin, "GET", f"{BASE}/api/audit/logs/?limit=20")
    t.add(step)
    if r_logs is None or r_logs.status_code != 200:
        results.append(t.to_fail(
            "Method: as admin, GET /api/audit/logs/?limit=20.\n"
            "Expected: HTTP 200 with at least 4 recent entries.\n"
            f"Observed: HTTP {r_logs.status_code if r_logs else 'no response'}."
        ))
        return _add_append_only(results)

    try:
        logs = r_logs.json()
        if isinstance(logs, dict):
            logs = logs.get("results", logs)
    except Exception:
        logs = []

    actions_seen = {row.get("action") for row in logs if isinstance(row, dict)}
    expected_subset = {"auth.login.success", "appointment.create", "appointment.update"}
    have_enough = len(logs) >= 4 and expected_subset.issubset(actions_seen)
    if have_enough:
        results.append(t.to_pass(
            "Method: as patient A book and cancel (PATCH status) an appointment, then as admin GET /api/audit/logs/.\n"
            "Expected: >=4 audit rows including auth.login.success, appointment.create, appointment.update.\n"
            f"Observed: {len(logs)} rows; saw actions {sorted(actions_seen)[:8]}."
        ))
    else:
        results.append(t.to_fail(
            "Method: as patient A book and cancel (PATCH status) an appointment, then as admin GET /api/audit/logs/.\n"
            "Expected: >=4 audit rows including auth.login.success, appointment.create, appointment.update.\n"
            f"Observed: {len(logs)} rows; missing one of expected actions: "
            f"{expected_subset - actions_seen}."
        ))

    return _add_append_only(results)


APPEND_ONLY_CODE = """
import sys
from django.core.exceptions import ValidationError
from audit.models import AuditLogEntry

entry = AuditLogEntry.objects.first()
if entry is None:
    print("NO_ROWS")
    sys.exit(0)

update_blocked = False
delete_blocked = False
try:
    entry.action = 'TAMPERED'
    entry.save()
except (ValidationError, Exception) as exc:
    update_blocked = True
    print(f'UPDATE_BLOCKED: {exc.__class__.__name__}: {exc}')

try:
    entry.delete()
except (ValidationError, Exception) as exc:
    delete_blocked = True
    print(f'DELETE_BLOCKED: {exc.__class__.__name__}: {exc}')

print(f'RESULT: update_blocked={update_blocked}, delete_blocked={delete_blocked}')
"""


def _add_append_only(results):
    t = TestRun("test_sr05_audit_append_only", ["SR-5"],
                "Audit log is append-only (cannot update or delete)")
    res = django_shell(APPEND_ONLY_CODE, timeout=30)
    stdout = res.stdout or ""
    stderr = res.stderr or ""
    captured = {
        "request": {"method": "SHELL", "url": "manage.py shell -c <append-only check>", "headers": {}},
        "response": {"status": res.returncode, "headers": {}, "body": stdout + ("\n--- stderr ---\n" + stderr if stderr else "")},
    }
    t.add(captured)

    update_blocked = "UPDATE_BLOCKED" in stdout
    delete_blocked = "DELETE_BLOCKED" in stdout
    if update_blocked and delete_blocked:
        results.append(t.to_pass(
            "Method: via Django shell, fetch first AuditLogEntry; attempt save() and delete().\n"
            "Expected: both raise an exception.\n"
            f"Observed: save() blocked = {update_blocked}; delete() blocked = {delete_blocked}.",
            notes="Append-only enforced at model save()/delete() override.",
        ))
    elif "NO_ROWS" in stdout:
        results.append(t.to_skip("Audit log was empty; cannot test append-only behavior."))
    else:
        results.append(t.to_fail(
            "Method: via Django shell, fetch first AuditLogEntry; attempt save() and delete().\n"
            "Expected: both raise an exception.\n"
            f"Observed: save() blocked = {update_blocked}; delete() blocked = {delete_blocked}.\n"
            f"Shell output: {stdout[:500]}"
        ))
    return results
