"""SR-7: MFA enforced for staff with TOTP enabled."""

from __future__ import annotations

import os
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from test_harness import TestRun, capture, django_shell, login  # noqa: E402

import requests

BASE = os.environ["APP_BASE_URL"]
DOCTOR = os.environ["DOCTOR_USERNAME"]
DOCTOR_PW = os.environ["DOCTOR_PASSWORD"]


ENABLE_TOTP = textwrap.dedent("""
    from accounts.models import User
    from django_otp.plugins.otp_totp.models import TOTPDevice

    u = User.objects.get(username='{username}')
    u.otp_required = True
    u.save(update_fields=['otp_required'])

    device, created = TOTPDevice.objects.get_or_create(
        user=u, name='manual-test',
        defaults={{'confirmed': True}},
    )
    device.confirmed = True
    device.save()
    print('OK')
""").strip()


DISABLE_TOTP = textwrap.dedent("""
    from accounts.models import User
    from django_otp.plugins.otp_totp.models import TOTPDevice

    u = User.objects.get(username='{username}')
    u.otp_required = False
    u.save(update_fields=['otp_required'])
    TOTPDevice.objects.filter(user=u, name='manual-test').delete()
    print('OK')
""").strip()


def _post_login(payload: dict) -> tuple[requests.Response | None, dict]:
    s = requests.Session()
    try:
        r = s.post(f"{BASE}/api/auth/login/", json=payload, timeout=10)
        return r, capture("POST", f"{BASE}/api/auth/login/", r, {"json": payload})
    except requests.RequestException as exc:
        step = capture("POST", f"{BASE}/api/auth/login/", None, {"json": payload})
        step["response"]["body"] = f"(transport error: {exc})"
        return None, step


def run():
    t = TestRun("test_sr07_mfa", ["SR-7"], "MFA enforced when TOTP device is configured")

    # Enable TOTP for doctor
    setup = django_shell(ENABLE_TOTP.format(username=DOCTOR), timeout=30)
    t.add({
        "request": {"method": "SHELL", "url": "manage.py shell -c <enable-totp>", "headers": {}},
        "response": {"status": setup.returncode, "headers": {}, "body": setup.stdout + setup.stderr},
    })
    if "OK" not in setup.stdout:
        return [t.to_skip(f"Could not enable TOTP for {DOCTOR}; shell stderr: {setup.stderr[:200]}")]

    try:
        # Attempt 1: username + password, no OTP
        r1, step1 = _post_login({"username": DOCTOR, "password": DOCTOR_PW})
        t.add(step1)
        cookie_header_1 = step1["response"]["headers"].get("set-cookie") or step1["response"]["headers"].get("Set-Cookie")
        body_1 = step1["response"]["body"]
        no_session_1 = (r1 is None) or (r1.status_code != 200) or ("clinic_access_token" not in (cookie_header_1 or ""))

        # Attempt 2: with a wrong OTP
        r2, step2 = _post_login({"username": DOCTOR, "password": DOCTOR_PW, "otp_token": "000000"})
        t.add(step2)
        cookie_header_2 = step2["response"]["headers"].get("set-cookie") or step2["response"]["headers"].get("Set-Cookie")
        no_session_2 = (r2 is None) or (r2.status_code != 200) or ("clinic_access_token" not in (cookie_header_2 or ""))

        if no_session_1 and no_session_2:
            return [t.to_pass(
                "Method: enable TOTP for test_doctor; POST login with no OTP, then with wrong OTP.\n"
                "Expected: neither attempt yields a fully authenticated session (no auth cookie set).\n"
                f"Observed: no-OTP -> HTTP {r1.status_code if r1 is not None else 'no response'}; "
                f"wrong-OTP -> HTTP {r2.status_code if r2 is not None else 'no response'}.",
                notes="Login serializer raises 'OTP verification failed.' before issuing tokens.",
            )]
        return [t.to_fail(
            "Method: enable TOTP for test_doctor; POST login with no OTP, then with wrong OTP.\n"
            "Expected: neither attempt yields a session.\n"
            f"Observed: no-OTP no_session={no_session_1}, wrong-OTP no_session={no_session_2}; "
            f"set-cookie 1: {cookie_header_1!r}; set-cookie 2: {cookie_header_2!r}."
        )]
    finally:
        # Disable TOTP again so other tests can log in as doctor normally.
        teardown = django_shell(DISABLE_TOTP.format(username=DOCTOR), timeout=30)
        t.add({
            "request": {"method": "SHELL", "url": "manage.py shell -c <disable-totp>", "headers": {}},
            "response": {"status": teardown.returncode, "headers": {}, "body": teardown.stdout + teardown.stderr},
        })
