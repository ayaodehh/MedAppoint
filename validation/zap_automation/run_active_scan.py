"""Run a ZAP active scan limited to localhost:3000 and write reports."""

from __future__ import annotations

import os
import sys
import time
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from zapv2 import ZAPv2

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
REPORT_DIR = ROOT / "validation" / "zap"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(HERE / ".env")

ZAP_API_KEY = os.environ.get("ZAP_API_KEY", "")
ZAP_PROXY = os.environ["ZAP_PROXY"]
APP_BASE_URL = os.environ["APP_BASE_URL"].rstrip("/")

PROXIES = {"http": ZAP_PROXY, "https": ZAP_PROXY}

CONTEXT_NAME = "MedAppoint"
SCOPE_REGEX = r"^http://localhost:3000(?:/.*)?$"
EXCLUDE_REGEXES = [
    r"^https?://[^/]*googleapis\.com.*$",
    r"^https?://[^/]*google\.com.*$",
    r"^https?://[^/]*gstatic\.com.*$",
    r"^https?://[^/]*accounts\.google\.com.*$",
    r"^https?://[^/]*fonts\.googleapis\.com.*$",
    r"^https?://[^/]*fonts\.gstatic\.com.*$",
]


def info(msg: str) -> None:
    print(f"[scan] {msg}")


def fail(msg: str) -> None:
    print(f"[scan][ERROR] {msg}", file=sys.stderr)
    sys.exit(1)


def connect() -> ZAPv2:
    info(f"Connecting to ZAP at {ZAP_PROXY}...")
    try:
        zap = ZAPv2(apikey=ZAP_API_KEY, proxies=PROXIES)
        info(f"  ZAP version: {zap.core.version}")
        return zap
    except Exception as exc:
        fail(f"Could not reach ZAP at {ZAP_PROXY}: {exc}")
        raise SystemExit(1)


def ensure_context(zap: ZAPv2) -> str:
    existing = zap.context.context_list
    if CONTEXT_NAME not in existing:
        info(f"Creating context {CONTEXT_NAME!r}.")
        zap.context.new_context(CONTEXT_NAME)
    else:
        info(f"Context {CONTEXT_NAME!r} already exists.")

    info(f"Scoping context to {SCOPE_REGEX}.")
    zap.context.include_in_context(CONTEXT_NAME, SCOPE_REGEX)
    for rx in EXCLUDE_REGEXES:
        zap.context.exclude_from_context(CONTEXT_NAME, rx)
    return CONTEXT_NAME


def configure_scan_scope(zap: ZAPv2) -> None:
    info("Excluding third-party origins from active scanning globally.")
    for rx in EXCLUDE_REGEXES:
        try:
            zap.ascan.exclude_from_scan(rx)
        except Exception as exc:
            info(f"  exclude_from_scan({rx}) returned: {exc}")


def start_scan(zap: ZAPv2) -> str:
    info(f"Starting active scan against {APP_BASE_URL} ...")
    scan_id = zap.ascan.scan(
        url=APP_BASE_URL,
        recurse=True,
        inscopeonly=True,
        scanpolicyname=None,
        method=None,
        postdata=None,
    )
    if not str(scan_id).isdigit():
        fail(f"Active scan did not start: {scan_id}")
    info(f"  scan id: {scan_id}")
    return str(scan_id)


def poll(zap: ZAPv2, scan_id: str, every_seconds: int = 30) -> None:
    while True:
        status = zap.ascan.status(scan_id)
        try:
            pct = int(status)
        except (TypeError, ValueError):
            pct = -1
        try:
            scan_progress = zap.ascan.scan_progress(scan_id)
            current_rule = "?"
            if isinstance(scan_progress, list):
                for entry in scan_progress:
                    if isinstance(entry, dict):
                        for host_block in entry.values():
                            if isinstance(host_block, list):
                                for plugin in host_block:
                                    if isinstance(plugin, dict) and plugin.get("status") == "Running":
                                        current_rule = plugin.get("name", "?")
                                        break
        except Exception:
            current_rule = "?"
        info(f"  progress: {pct}%  | running: {current_rule}")
        if pct >= 100:
            return
        time.sleep(every_seconds)


def summarise_alerts(zap: ZAPv2) -> Counter:
    alerts = zap.core.alerts(baseurl=APP_BASE_URL)
    counts: Counter = Counter()
    for a in alerts:
        risk = a.get("risk", "Informational")
        counts[risk] += 1
    return counts


def write_summary(counts: Counter) -> Path:
    out = REPORT_DIR / "zap_active_summary.txt"
    lines = [
        "MedAppoint - ZAP active scan summary",
        "------------------------------------",
        f"Target:      {APP_BASE_URL}",
        f"High:        {counts.get('High', 0)}",
        f"Medium:      {counts.get('Medium', 0)}",
        f"Low:         {counts.get('Low', 0)}",
        f"Informational: {counts.get('Informational', 0)}",
        f"Total:       {sum(counts.values())}",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def write_html_report(zap: ZAPv2) -> Path:
    out = REPORT_DIR / "zap_active.html"
    info(f"Generating HTML report -> {out}")
    try:
        zap.reports.generate(
            title="MedAppoint Active Scan",
            template="traditional-html",
            sites=APP_BASE_URL,
            reportfilename="zap_active.html",
            reportdir=str(REPORT_DIR.resolve()),
        )
        if out.exists():
            return out
    except Exception as exc:
        info(f"  reports.generate failed ({exc}); falling back to core.htmlreport().")

    html = zap.core.htmlreport()
    out.write_text(html, encoding="utf-8")
    return out


def main() -> None:
    zap = connect()
    ensure_context(zap)
    configure_scan_scope(zap)
    scan_id = start_scan(zap)
    poll(zap, scan_id, every_seconds=30)

    counts = summarise_alerts(zap)
    info("---")
    info("Alert summary:")
    info(f"  High:          {counts.get('High', 0)}")
    info(f"  Medium:        {counts.get('Medium', 0)}")
    info(f"  Low:           {counts.get('Low', 0)}")
    info(f"  Informational: {counts.get('Informational', 0)}")
    info(f"  Total:         {sum(counts.values())}")

    summary_path = write_summary(counts)
    html_path = write_html_report(zap)
    info(f"Wrote summary: {summary_path}")
    info(f"Wrote HTML:    {html_path}")
    info("Done.")


if __name__ == "__main__":
    main()
