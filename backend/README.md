# Clinic Appointment System API

Django REST API scaffold for a clinic appointment system with role-based access control, cookie-based JWT authentication, OTP support, Axes lockout protection, append-only audit logging, and stubbed billing/EHR integrations.

## Included apps

- `accounts`
- `patients`
- `appointments`
- `clinical`
- `billing`
- `ehr`
- `audit`

## Features

- Custom `accounts.User` model with role field
- Django REST Framework API with default-deny permissions
- `djangorestframework-simplejwt` using HTTP-only cookies
- `django-axes` login protection
- `django-otp` TOTP device setup and verification
- Argon2 password hashing
- CORS support via `django-cors-headers`
- Append-only `AuditLogEntry` rows for auth events and state-changing endpoints
- Stubbed integration points in `billing/services.py` and `ehr/services.py`

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Copy environment values:

```powershell
Copy-Item .env.example .env
```

4. Create migrations and migrate:

```powershell
python manage.py makemigrations accounts patients appointments clinical billing ehr audit
python manage.py migrate
```

5. Create an admin user:

```powershell
python manage.py createsuperuser
```

6. Run the server:

```powershell
python manage.py runserver
```

## API notes

- Base path: `/api/`
- Auth endpoints:
  - `POST /api/auth/register/`
  - `POST /api/auth/login/`
  - `POST /api/auth/refresh/`
  - `POST /api/auth/logout/`
  - `POST /api/auth/otp_setup/`
  - `POST /api/auth/otp_verify/`
- Resource endpoints are registered through DRF routers under `/api/`.
- Patients only see their own linked records.
- Auditors are read-only and limited to audit and read access.

## Stub integrations

- Payment stub: `billing/services.py::process_payment_stub`
- EHR stub: `ehr/services.py::sync_ehr_record_stub`

Neither function makes a real network call.
