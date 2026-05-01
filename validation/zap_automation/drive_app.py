"""Drive MedAppoint through ZAP's proxy so the active scan has real coverage.

Logs in as patient and as staff via the API, exercises authenticated
endpoints, then GETs a handful of frontend pages so ZAP's Sites tree includes
the HTML/JS routes too.
"""

from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests
import urllib3
from dotenv import load_dotenv
from zapv2 import ZAPv2

HERE = Path(__file__).resolve().parent
load_dotenv(HERE / ".env")

ZAP_API_KEY = os.environ.get("ZAP_API_KEY", "")
ZAP_PROXY = os.environ["ZAP_PROXY"]
APP_BASE_URL = os.environ["APP_BASE_URL"].rstrip("/")
API_BASE = f"{APP_BASE_URL}/api"

PATIENT_USERNAME = os.environ["PATIENT_USERNAME"]
PATIENT_PASSWORD = os.environ["PATIENT_PASSWORD"]
STAFF_USERNAME = os.environ["STAFF_USERNAME"]
STAFF_PASSWORD = os.environ["STAFF_PASSWORD"]

PROXIES = {"http": ZAP_PROXY, "https": ZAP_PROXY}
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REQUEST_COUNT = 0


def info(msg: str) -> None:
    print(f"[drive] {msg}")


def fail(msg: str) -> None:
    print(f"[drive][ERROR] {msg}", file=sys.stderr)
    sys.exit(1)


def confirm_zap() -> None:
    info(f"Connecting to ZAP at {ZAP_PROXY}...")
    try:
        zap = ZAPv2(apikey=ZAP_API_KEY, proxies=PROXIES)
        version = zap.core.version
        info(f"  ZAP version: {version}")
    except Exception as exc:
        fail(
            f"Could not reach ZAP at {ZAP_PROXY}.\n"
            f"  Make sure ZAP is running in daemon mode and the API key is correct.\n"
            f"  Underlying error: {exc}"
        )


def proxied_session() -> requests.Session:
    s = requests.Session()
    s.proxies.update(PROXIES)
    s.verify = False
    s.headers.update({"User-Agent": "MedAppoint-ZAP-Driver/1.0"})
    return s


def hit(session: requests.Session, method: str, url: str, **kwargs) -> requests.Response | None:
    global REQUEST_COUNT
    REQUEST_COUNT += 1
    try:
        r = session.request(method, url, timeout=15, **kwargs)
        info(f"  {method:6s} {url}  -> {r.status_code}")
        return r
    except requests.RequestException as exc:
        info(f"  {method:6s} {url}  -> ERROR ({exc})")
        return None


def login(session: requests.Session, username: str, password: str) -> bool:
    r = hit(session, "POST", f"{API_BASE}/auth/login/", json={"username": username, "password": password})
    if r is None:
        return False
    if r.status_code != 200:
        info(f"  login failed for {username!r}: {r.status_code} {r.text[:200]}")
        return False
    info(f"  logged in as {username!r}; cookies: {sorted(session.cookies.keys())}")
    return True


def patient_flow() -> None:
    info("=== Patient flow ===")
    s = proxied_session()
    if not login(s, PATIENT_USERNAME, PATIENT_PASSWORD):
        info("  skipping patient flow.")
        return

    hit(s, "GET", f"{API_BASE}/accounts/users/me/")
    hit(s, "GET", f"{API_BASE}/auth/me/")            # may 404 - intentional
    hit(s, "GET", f"{API_BASE}/patients/")
    hit(s, "GET", f"{API_BASE}/patients/me/")        # may 404 - intentional
    hit(s, "GET", f"{API_BASE}/appointments/")

    tomorrow = (dt.date.today() + dt.timedelta(days=1)).isoformat()
    hit(s, "GET", f"{API_BASE}/appointments/slots/?date={tomorrow}")  # may 404

    # Try to book and then cancel an appointment.
    patients_resp = hit(s, "GET", f"{API_BASE}/patients/")
    patient_id = None
    if patients_resp is not None and patients_resp.status_code == 200:
        try:
            data = patients_resp.json()
            results = data.get("results", data) if isinstance(data, dict) else data
            if results:
                patient_id = results[0].get("id")
        except ValueError:
            patient_id = None

    if patient_id:
        start = dt.datetime.combine(dt.date.today() + dt.timedelta(days=1), dt.time(10, 0))
        end = start + dt.timedelta(minutes=30)
        body = {
            "patient": patient_id,
            "scheduled_start": start.isoformat() + "Z",
            "scheduled_end": end.isoformat() + "Z",
            "reason": "ZAP automation test booking",
            "status": "requested",
        }
        booked = hit(s, "POST", f"{API_BASE}/appointments/", json=body)
        hit(s, "GET", f"{API_BASE}/appointments/")
        if booked is not None and booked.status_code in (200, 201):
            try:
                appt_id = booked.json().get("id")
            except ValueError:
                appt_id = None
            if appt_id is not None:
                hit(s, "DELETE", f"{API_BASE}/appointments/{appt_id}/")
    else:
        info("  no patient row visible to this user; skipping booking POST.")


def staff_flow() -> None:
    info("=== Staff (admin) flow ===")
    s = proxied_session()
    if not login(s, STAFF_USERNAME, STAFF_PASSWORD):
        info("  skipping staff flow.")
        return

    hit(s, "GET", f"{API_BASE}/accounts/users/me/")
    hit(s, "GET", f"{API_BASE}/auth/me/")            # may 404
    hit(s, "GET", f"{API_BASE}/accounts/users/")
    hit(s, "GET", f"{API_BASE}/appointments/")
    hit(s, "GET", f"{API_BASE}/clinical/notes/")
    hit(s, "GET", f"{API_BASE}/billing/invoices/")
    hit(s, "GET", f"{API_BASE}/audit/logs/")


FRONTEND_PATHS = [
    "/",
    "/login",
    "/register",
    "/dashboard",
    "/appointments",
    "/book",
    "/staff/login",
    "/staff/schedule",
    "/staff/audit",
]


def frontend_browse() -> None:
    info("=== Frontend browse ===")
    s = proxied_session()
    for path in FRONTEND_PATHS:
        hit(s, "GET", urljoin(APP_BASE_URL + "/", path.lstrip("/")))


def main() -> None:
    confirm_zap()
    patient_flow()
    staff_flow()
    frontend_browse()
    info("---")
    info(f"Total requests sent through ZAP: {REQUEST_COUNT}")
    info("Done. ZAP's Sites tree should now contain the API and frontend paths.")


if __name__ == "__main__":
    main()
