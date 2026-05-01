# MedAppoint - Manual Functional Security Tests

Automated functional tests for the seven security requirements that ZAP
can't easily cover. Treats the running prototype as a black box, captures
every request/response, and writes a Word-pasteable summary plus a JSON
evidence file.

## Preconditions

1. Django backend on `http://127.0.0.1:8000` and Next.js frontend on
   `http://localhost:3000` already running.
2. Python venv with deps installed:
   ```powershell
   pip install -r validation/manual_tests/requirements.txt
   ```
3. `.env` exists. Copy from template and edit if needed:
   ```powershell
   copy validation\manual_tests\.env.example validation\manual_tests\.env
   ```
4. Backend's venv at `backend/venv/` is what `seed_test_users.py` uses to
   shell out to `manage.py` for staff creation and lockout cleanup.

## Run

```powershell
python validation\manual_tests\run_all_tests.py
```

This will:
1. Verify `APP_BASE_URL` is reachable (otherwise stop).
2. Run `seed_test_users.py` (idempotent — registers patients via API and
   creates staff via Django shell).
3. Discover and run every `tests/test_*.py` in alphabetical order.
4. Write:
   - `validation/manual_tests/manual_tests_summary.txt`
   - `validation/manual_tests/manual_tests_evidence.json`
5. Print a coloured pass/fail table.

## Notes about this prototype

- The spec mentions endpoints `/api/patients/me/` and `/api/auth/me/` that
  do not exist in this build. Tests use `/api/patients/` (filtered to the
  caller for patients) and `/api/accounts/users/me/` (the real "me").
- `LoginSerializer` enforces OTP whenever a confirmed TOTPDevice exists
  for the user. SR-7 enables a TOTPDevice on `test_doctor` directly via
  Django shell so the test can exercise the OTP gate without needing a
  real authenticator app.
- SR-13 swaps to admin for the actual invoice POST because receptionist
  is forbidden by `BillingPermission`. Both observations are recorded in
  the evidence.
- SR-3 uses a throwaway username so it doesn't lock out a real test
  account. SR-8 deliberately locks `test_patient_a` and unlocks it via
  `python manage.py axes_reset_username` afterwards.
- No application code is modified. Staff creation goes through
  `manage.py shell -c` in `seed_test_users.py`.
