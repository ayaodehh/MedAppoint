"""Idempotently ensure the ZAP test patient and staff admin exist.

Patient is created via the public registration API.
Staff admin is created (or updated) via Django shell, because registration
forces the patient role.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import requests
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BACKEND_DIR = ROOT / "backend"

load_dotenv(HERE / ".env")

API_BASE = "http://127.0.0.1:8000/api"
PATIENT_USERNAME = os.environ["PATIENT_USERNAME"]
PATIENT_PASSWORD = os.environ["PATIENT_PASSWORD"]
STAFF_USERNAME = os.environ["STAFF_USERNAME"]
STAFF_PASSWORD = os.environ["STAFF_PASSWORD"]


def info(msg: str) -> None:
    print(f"[seed] {msg}")


def fail(msg: str) -> None:
    print(f"[seed][ERROR] {msg}", file=sys.stderr)
    sys.exit(1)


def venv_python() -> Path:
    """Return the venv's Python on Windows or POSIX."""
    win = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
    posix = BACKEND_DIR / "venv" / "bin" / "python"
    if win.exists():
        return win
    if posix.exists():
        return posix
    fail(f"Could not find backend venv Python at {win} or {posix}.")
    raise SystemExit(1)


def ensure_patient() -> None:
    info(f"Ensuring patient '{PATIENT_USERNAME}' exists...")
    payload = {
        "username": PATIENT_USERNAME,
        "email": f"{PATIENT_USERNAME}@example.test",
        "password": PATIENT_PASSWORD,
        "first_name": "Zap",
        "last_name": "Tester",
        "phone_number": "+10000000000",
        "medical_record_number": f"MRN-{PATIENT_USERNAME}",
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
    if r.status_code == 400:
        body = r.text.lower()
        if "already" in body or "exists" in body or "unique" in body:
            info("  already exists - leaving as-is.")
            return
    fail(f"Patient registration failed: {r.status_code} {r.text}")


STAFF_SHELL = textwrap.dedent(
    """
    from accounts.models import User

    username = "{username}"
    password = "{password}"

    user, created = User.objects.get_or_create(
        username=username,
        defaults={{
            "email": f"{{username}}@example.test",
            "first_name": "Admin",
            "last_name": "Staff",
            "role": "admin",
            "is_staff": True,
            "is_superuser": True,
        }},
    )
    user.role = "admin"
    user.is_staff = True
    user.is_superuser = True
    user.set_password(password)
    user.save()
    print("created" if created else "updated")
    """
).strip()


def ensure_staff_admin() -> None:
    info(f"Ensuring staff admin '{STAFF_USERNAME}' exists (via Django shell)...")
    py = venv_python()
    code = STAFF_SHELL.format(username=STAFF_USERNAME, password=STAFF_PASSWORD)
    cmd = [str(py), "manage.py", "shell", "-c", code]
    try:
        result = subprocess.run(
            cmd,
            cwd=BACKEND_DIR,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        fail("Django shell timed out while creating the staff admin.")
        return
    if result.returncode != 0:
        fail(
            "Django shell failed while creating the staff admin.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    info(f"  {result.stdout.strip() or 'done'}.")


def main() -> None:
    info("Starting user seeding.")
    ensure_patient()
    ensure_staff_admin()
    info("Done.")


if __name__ == "__main__":
    main()
