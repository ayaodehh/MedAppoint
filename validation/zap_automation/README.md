# MedAppoint - ZAP Active-Scan Automation

This folder replaces the unreliable "Manual Explore" step of OWASP ZAP with a
repeatable Python harness that drives the application through the ZAP proxy
and then runs an active scan.

## What it does

1. `seed_users.py` ensures the test patient and staff admin exist.
2. `drive_app.py` logs in as patient and as staff via the API, exercises a
   set of authenticated endpoints, and browses several frontend pages so
   ZAP's Sites tree is fully populated.
3. `run_active_scan.py` runs an active scan limited to `localhost:3000`,
   polls progress, then writes:
     - `validation/zap/zap_active.html`           (full HTML report)
     - `validation/zap/zap_active_summary.txt`    (alert counts)

## Preconditions

1. **OWASP ZAP installed** and reachable. Start it in daemon mode with the
   API enabled:
   ```powershell
   & "C:\Program Files\OWASP\Zed Attack Proxy\zap.bat" -daemon -port 8090
   ```
   Or start ZAP normally and confirm the API at `Tools -> Options -> API`.
2. **API key**: copy it from `Tools -> Options -> API` into `.env` as
   `ZAP_API_KEY`.
3. **Both servers running locally**:
   - Django backend on `http://127.0.0.1:8000`
   - Next.js frontend on `http://localhost:3000`
4. **Python venv**: install dependencies once.
   ```powershell
   pip install -r validation/zap_automation/requirements.txt
   ```
   The official ZAP client is published as `zaproxy` (formerly
   `python-owasp-zap-v2.4`) and exposes `from zapv2 import ZAPv2`. If your
   environment cannot find `zaproxy`, install `python-owasp-zap-v2.4`
   instead - the code is identical.
5. **Environment file**: copy `.env.example` to `.env` and fill in
   `ZAP_API_KEY`. Do not commit `.env`.

## Run order

```powershell
copy .env.example .env
# edit .env, paste your ZAP API key

# one-shot wrapper
.\validation\zap_automation\run_all.ps1
```

Or run the three steps manually:

```powershell
python validation/zap_automation/seed_users.py
python validation/zap_automation/drive_app.py
python validation/zap_automation/run_active_scan.py
```

## Notes about this prototype

- The active scan is scoped to `http://localhost:3000` only. Third-party
  origins (Google Fonts, googleapis.com, accounts.google.com) are excluded
  so the scan finishes in a reasonable time.
- A few of the URLs the harness probes do not exist in this build of the
  prototype (`/api/auth/me/`, `/api/patients/me/`, `/api/appointments/slots/`).
  Those will return 404, which is intentional - the goal is to populate
  ZAP's Sites tree with realistic paths the API surface might expose.
- Cookie-based auth: the API uses `HttpOnly` cookies
  (`clinic_access_token`, `clinic_refresh_token`). The harness lets
  `requests.Session` capture them automatically; ZAP records the same
  traffic because it sits in the middle as the configured proxy.
- The script does not modify any application code. It is a pure testing
  harness.
