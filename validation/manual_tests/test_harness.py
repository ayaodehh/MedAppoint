"""Shared utilities for the MedAppoint manual functional security tests."""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable

import requests
from dotenv import load_dotenv

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init()
except Exception:  # pragma: no cover
    class _Stub:
        def __getattr__(self, _): return ""
    Fore = Style = _Stub()  # type: ignore

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BACKEND_DIR = ROOT / "backend"

REQUEST_TIMEOUT = 10
MAX_BODY_CAPTURE = 2000


@dataclass
class Step:
    request: dict
    response: dict


@dataclass
class Result:
    test_id: str
    sr_ids: list[str]
    name: str
    passed: bool | None  # True/False/None where None == SKIPPED
    started_at: str
    duration_ms: int
    steps: list[dict] = field(default_factory=list)
    notes: str = ""
    summary: str = ""           # short Method/Expected/Observed paragraph
    skipped_reason: str = ""

    @property
    def status(self) -> str:
        if self.passed is True:
            return "PASS"
        if self.passed is False:
            return "FAIL"
        return "SKIP"


def load_env() -> dict[str, str]:
    load_dotenv(HERE / ".env")
    required = [
        "APP_BASE_URL",
        "PATIENT_A_USERNAME", "PATIENT_A_PASSWORD",
        "PATIENT_B_USERNAME", "PATIENT_B_PASSWORD",
        "RECEPTIONIST_USERNAME", "RECEPTIONIST_PASSWORD",
        "DOCTOR_USERNAME", "DOCTOR_PASSWORD",
        "ADMIN_USERNAME", "ADMIN_PASSWORD",
    ]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"[harness] Missing required .env keys: {', '.join(missing)}")
    return {k: os.environ[k] for k in required}


def venv_python() -> Path:
    win = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
    posix = BACKEND_DIR / "venv" / "bin" / "python"
    if win.exists():
        return win
    if posix.exists():
        return posix
    raise SystemExit(f"[harness] backend venv Python not found at {win} or {posix}")


def django_shell(code: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a snippet inside Django's shell, capturing stdout/stderr."""
    py = venv_python()
    return subprocess.run(
        [str(py), "manage.py", "shell", "-c", code],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def django_manage(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    py = venv_python()
    return subprocess.run(
        [str(py), "manage.py", *args],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# HTTP helpers


def truncate(text: str, n: int = MAX_BODY_CAPTURE) -> str:
    if text is None:
        return ""
    if len(text) <= n:
        return text
    return text[:n] + f"... [truncated {len(text) - n} chars]"


def capture(method: str, url: str, response: requests.Response | None,
            request_kwargs: dict | None = None) -> dict:
    """Build a step dict from a finished request."""
    request_kwargs = request_kwargs or {}
    request_dict = {"method": method.upper(), "url": url, "headers": {}}
    body = request_kwargs.get("json")
    if body is not None:
        request_dict["json"] = body
    if "data" in request_kwargs:
        request_dict["data"] = str(request_kwargs.get("data"))[:500]
    if response is None:
        response_dict = {"status": None, "headers": {}, "body": "(no response)"}
    else:
        # Capture only a safe subset of response headers for evidence.
        safe_headers = {
            k: v for k, v in response.headers.items()
            if k.lower() in {"content-type", "set-cookie", "www-authenticate", "retry-after", "x-frame-options", "content-security-policy"}
        }
        try:
            body_text = truncate(response.text)
        except Exception:
            body_text = "(body unavailable)"
        response_dict = {"status": response.status_code, "headers": safe_headers, "body": body_text}
    return {"request": request_dict, "response": response_dict}


def http(session: requests.Session, method: str, url: str, **kwargs) -> tuple[requests.Response | None, dict]:
    """Issue a request, return (response_or_None, captured_step_dict)."""
    kwargs.setdefault("timeout", REQUEST_TIMEOUT)
    try:
        r = session.request(method, url, **kwargs)
        return r, capture(method, url, r, kwargs)
    except requests.RequestException as exc:
        step = capture(method, url, None, kwargs)
        step["response"]["body"] = f"(transport error: {exc})"
        return None, step


def login(base_url: str, username: str, password: str,
          otp_token: str | None = None) -> tuple[requests.Session | None, dict]:
    """Try to log in. Return (session_or_None, captured_step). Session has cookies if successful."""
    s = requests.Session()
    body: dict[str, Any] = {"username": username, "password": password}
    if otp_token is not None:
        body["otp_token"] = otp_token
    r, step = http(s, "POST", f"{base_url}/api/auth/login/", json=body)
    if r is not None and r.status_code == 200 and "clinic_access_token" in s.cookies:
        return s, step
    return None, step


# ---------------------------------------------------------------------------
# Result helpers used by tests


class TestRun:
    """Convenience accumulator a test can use to build its Result."""

    def __init__(self, test_id: str, sr_ids: list[str], name: str):
        self.test_id = test_id
        self.sr_ids = sr_ids
        self.name = name
        self.steps: list[dict] = []
        self.started_at = dt.datetime.now().isoformat(timespec="seconds")
        self._t0 = time.time()

    def add(self, step: dict) -> None:
        self.steps.append(step)

    def to_pass(self, summary: str, notes: str = "") -> Result:
        return self._finish(True, summary, notes)

    def to_fail(self, summary: str, notes: str = "") -> Result:
        return self._finish(False, summary, notes)

    def to_skip(self, reason: str) -> Result:
        r = self._finish(None, summary=f"Skipped: {reason}", notes="")
        r.skipped_reason = reason
        return r

    def _finish(self, passed: bool | None, summary: str, notes: str) -> Result:
        return Result(
            test_id=self.test_id,
            sr_ids=self.sr_ids,
            name=self.name,
            passed=passed,
            started_at=self.started_at,
            duration_ms=int((time.time() - self._t0) * 1000),
            steps=self.steps,
            notes=notes,
            summary=summary,
        )


# ---------------------------------------------------------------------------
# Console output


def print_pass(test_id: str, name: str) -> None:
    print(f"  {Fore.GREEN}PASS{Style.RESET_ALL}  {test_id:30s} {name}")


def print_fail(test_id: str, name: str, reason: str) -> None:
    print(f"  {Fore.RED}FAIL{Style.RESET_ALL}  {test_id:30s} {name}")
    if reason:
        print(f"        reason: {reason}")


def print_skip(test_id: str, name: str, reason: str) -> None:
    print(f"  {Fore.YELLOW}SKIP{Style.RESET_ALL}  {test_id:30s} {name}")
    if reason:
        print(f"        reason: {reason}")


def emit_result(r: Result) -> None:
    if r.passed is True:
        print_pass(r.test_id, r.name)
    elif r.passed is False:
        print_fail(r.test_id, r.name, r.summary)
    else:
        print_skip(r.test_id, r.name, r.skipped_reason or r.summary)


# ---------------------------------------------------------------------------
# Output writers


def write_outputs(results: Iterable[Result], output_dir: Path, target_url: str) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "manual_tests_summary.txt"
    evidence_path = output_dir / "manual_tests_evidence.json"

    results = list(results)
    sr_set = sorted({sr for r in results for sr in r.sr_ids})
    n_total = len(results)
    n_pass = sum(1 for r in results if r.passed is True)
    n_fail = sum(1 for r in results if r.passed is False)
    n_skip = sum(1 for r in results if r.passed is None)

    lines = [
        "MedAppoint - Manual Functional Tests Summary",
        "--------------------------------------------",
        f"Run at:        {dt.datetime.now().isoformat(timespec='seconds')}",
        f"Target:        {target_url}",
        f"Tests run:     {n_total}",
        f"Passed:        {n_pass}",
        f"Failed:        {n_fail}",
        f"Skipped:       {n_skip}",
        f"SR coverage:   {', '.join(sr_set)}",
        "",
    ]
    for i, r in enumerate(results, start=1):
        sr_label = ", ".join(r.sr_ids)
        lines.append(f"--- Test {i} [{sr_label}]: {r.name} ---")
        lines.append(f"Result: {r.status}")
        # summary text may contain its own newlines (Method/Expected/Observed lines)
        lines.append(r.summary)
        if r.notes:
            lines.append(f"Notes: {r.notes}")
        lines.append("")

    summary_path.write_text("\n".join(lines), encoding="utf-8")

    evidence = [
        {
            **{k: v for k, v in asdict(r).items() if k != "summary"},
            "status": r.status,
            "summary": r.summary,
        }
        for r in results
    ]
    evidence_path.write_text(json.dumps(evidence, indent=2, default=str), encoding="utf-8")
    return summary_path, evidence_path
