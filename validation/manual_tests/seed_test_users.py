"""Idempotently create the six test users the manual tests need.

Patients are created via the public registration API; staff (receptionist,
clinician/doctor, admin) are created or updated via Django shell because
registration always assigns the patient role. No application code is
modified.
"""

from __future__ import annotations

import os
import sys
import textwrap
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from test_harness import django_shell, load_env  # noqa: E402

API_BASE = "http://127.0.0.1:8000/api"


def info(msg: str) -> None:
    print(f"[seed] {msg}")


def fail(msg: str) -> None:
    print(f"[seed][ERROR] {msg}", file=sys.stderr)
    sys.exit(1)


def register_patient(username: str, password: str, mrn_suffix: str) -> None:
    info(f"Ensuring patient '{username}' exists...")
    payload = {
        "username": username,
        "email": f"{username}@example.test",
        "password": password,
        "first_name": username.replace("_", " ").title(),
        "last_name": "Tester",
        "phone_number": "+10000000000",
        "medical_record_number": f"MRN-{mrn_suffix}",
        "date_of_birth": "1990-01-01",
    }
    try:
        r = requests.post(f"{API_BASE}/auth/register/", json=payload, timeout=10)
    except requests.RequestException as exc:
        fail(f"Could not reach Django at {API_BASE}: {exc}")
        return
    if r.status_code == 201:
        info("  created.")
        return
    if r.status_code == 400 and any(s in r.text.lower() for s in ("already", "exists", "unique")):
        info("  already exists - leaving as-is.")
        return
    fail(f"Patient registration failed for {username}: {r.status_code} {r.text}")


STAFF_SHELL = textwrap.dedent(
    """
    from accounts.models import User

    spec = [
        ("{recept}", "{recept_pw}", "receptionist", False, False),
        ("{doctor}", "{doctor_pw}", "clinician",   False, False),
        ("{admin}",  "{admin_pw}",  "admin",       True,  True),
    ]

    for username, password, role, is_staff, is_superuser in spec:
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={{
                "email": f"{{username}}@example.test",
                "first_name": username.replace("_", " ").title(),
                "last_name": "Tester",
                "role": role,
                "is_staff": is_staff,
                "is_superuser": is_superuser,
            }},
        )
        user.role = role
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.set_password(password)
        user.save()
        print(f"ok {{username}} ({{role}})")
    """
).strip()


def ensure_staff(env: dict[str, str]) -> None:
    info("Ensuring staff users exist (via Django shell)...")
    code = STAFF_SHELL.format(
        recept=env["RECEPTIONIST_USERNAME"], recept_pw=env["RECEPTIONIST_PASSWORD"],
        doctor=env["DOCTOR_USERNAME"], doctor_pw=env["DOCTOR_PASSWORD"],
        admin=env["ADMIN_USERNAME"], admin_pw=env["ADMIN_PASSWORD"],
    )
    res = django_shell(code, timeout=60)
    if res.returncode != 0:
        fail(f"Django shell failed:\nstdout: {res.stdout}\nstderr: {res.stderr}")
    for line in res.stdout.splitlines():
        if line.startswith("ok "):
            info("  " + line[3:])


def main() -> None:
    env = load_env()
    info("Starting test-user seeding.")
    register_patient(env["PATIENT_A_USERNAME"], env["PATIENT_A_PASSWORD"], "PATA")
    register_patient(env["PATIENT_B_USERNAME"], env["PATIENT_B_PASSWORD"], "PATB")
    ensure_staff(env)
    info("Done.")


if __name__ == "__main__":
    main()
