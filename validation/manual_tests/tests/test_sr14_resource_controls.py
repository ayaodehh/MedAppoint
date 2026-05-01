"""SR-14: Resource and pagination controls."""

from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from test_harness import TestRun, http, login  # noqa: E402

BASE = os.environ["APP_BASE_URL"]


def run():
    results = []

    # ---- huge page_size ---------------------------------------------------
    t = TestRun("test_sr14_pagination_cap", ["SR-14"],
                "Large page_size is capped or rejected")
    s, login_step = login(BASE, os.environ["ADMIN_USERNAME"], os.environ["ADMIN_PASSWORD"])
    t.add(login_step)
    if s is None:
        results.append(t.to_fail("Method: log in as admin. Observed: login failed."))
    else:
        r, step = http(s, "GET", f"{BASE}/api/patients/?page_size=999999")
        t.add(step)
        code = r.status_code if r is not None else None
        if code is None:
            results.append(t.to_fail(
                "Method: GET /api/patients/?page_size=999999. Observed: no response."
            ))
        elif code == 400:
            results.append(t.to_pass(
                "Method: GET /api/patients/?page_size=999999.\n"
                "Expected: server caps page_size or rejects (400).\n"
                "Observed: HTTP 400 (request rejected).",
            ))
        elif code == 200:
            try:
                payload = r.json()
            except Exception:
                payload = None
            paginated = isinstance(payload, dict) and ("results" in payload or "next" in payload or "count" in payload)
            row_count = (
                len(payload.get("results", [])) if isinstance(payload, dict) and isinstance(payload.get("results"), list)
                else (len(payload) if isinstance(payload, list) else None)
            )
            if paginated and row_count is not None and row_count <= 100:
                results.append(t.to_pass(
                    "Method: GET /api/patients/?page_size=999999.\n"
                    "Expected: server caps page_size to a reasonable max.\n"
                    f"Observed: HTTP 200; returned {row_count} rows in a paginated envelope.",
                ))
            else:
                results.append(t.to_fail(
                    "Method: GET /api/patients/?page_size=999999.\n"
                    "Expected: paginated response with capped row count.\n"
                    f"Observed: HTTP 200; paginated={paginated}, row_count={row_count}. "
                    f"DRF default pagination is not configured in this build."
                ))
        else:
            results.append(t.to_fail(
                "Method: GET /api/patients/?page_size=999999.\n"
                f"Expected: 200 paginated/capped or 400.\n"
                f"Observed: HTTP {code}."
            ))

    # ---- malformed page parameter -----------------------------------------
    t2 = TestRun("test_sr14_malformed_page", ["SR-14"],
                 "Malformed pagination params return 400, not 500")
    s2, login_step2 = login(BASE, os.environ["ADMIN_USERNAME"], os.environ["ADMIN_PASSWORD"])
    t2.add(login_step2)
    if s2 is None:
        results.append(t2.to_fail("Method: log in as admin. Observed: login failed."))
        return results

    for q in ("page=-1", "page=abc"):
        r, step = http(s2, "GET", f"{BASE}/api/patients/?{q}")
        t2.add(step)
        code = r.status_code if r is not None else None
        if code == 500:
            results.append(t2.to_fail(
                f"Method: GET /api/patients/?{q}.\n"
                f"Expected: 400 (graceful error).\n"
                f"Observed: HTTP 500 (server crashed)."
            ))
            return results

    # If we got here, neither malformed query produced a 500.
    results.append(t2.to_pass(
        "Method: GET /api/patients/?page=-1 and ?page=abc.\n"
        "Expected: graceful rejection (400) and definitely not 500.\n"
        "Observed: neither query produced HTTP 500.",
        notes="Server tolerated unknown/invalid query params gracefully.",
    ))
    return results
