"""Orchestrator for the MedAppoint manual functional security tests."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import traceback
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from test_harness import (  # noqa: E402
    Result, TestRun, emit_result, load_env, write_outputs,
)

try:
    from colorama import Fore, Style
except Exception:  # pragma: no cover
    class _Stub:
        def __getattr__(self, _): return ""
    Fore = Style = _Stub()  # type: ignore


def banner(title: str) -> None:
    print()
    print(Fore.CYAN + "=" * 64 + Style.RESET_ALL)
    print(Fore.CYAN + f" {title}" + Style.RESET_ALL)
    print(Fore.CYAN + "=" * 64 + Style.RESET_ALL)


def verify_target(base_url: str) -> None:
    try:
        r = requests.get(base_url, timeout=5)
        print(f"[run_all] target reachable: {base_url} -> HTTP {r.status_code}")
    except requests.RequestException as exc:
        print(f"[run_all][ERROR] {base_url} not reachable: {exc}", file=sys.stderr)
        sys.exit(2)


def run_seed_script() -> None:
    banner("Step 1/2: seed test users")
    script = HERE / "seed_test_users.py"
    res = subprocess.run([sys.executable, str(script)], cwd=str(HERE))
    if res.returncode != 0:
        print(f"[run_all][ERROR] seed_test_users.py failed (exit {res.returncode}).", file=sys.stderr)
        sys.exit(res.returncode)


def discover_tests() -> list[Path]:
    return sorted((HERE / "tests").glob("test_*.py"))


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def run_tests() -> list[Result]:
    banner("Step 2/2: run tests")
    all_results: list[Result] = []
    for path in discover_tests():
        module_name = path.stem
        print()
        print(f"--- {module_name} ---")
        try:
            module = load_module(path)
            run = getattr(module, "run", None)
            if run is None:
                t = TestRun(module_name, [], "No run() function")
                all_results.append(t.to_fail("Test module exposes no run() function."))
                emit_result(all_results[-1])
                continue
            results = run() or []
            for r in results:
                if not isinstance(r, Result):
                    continue
                all_results.append(r)
                emit_result(r)
        except Exception:
            tb = traceback.format_exc()
            t = TestRun(module_name, [], "Unhandled exception")
            t.add({
                "request": {"method": "PYTHON", "url": module_name, "headers": {}},
                "response": {"status": -1, "headers": {}, "body": tb},
            })
            r = t.to_fail(f"Method: import and run {module_name}.\nObserved: unhandled exception.\n{tb.splitlines()[-1]}")
            all_results.append(r)
            emit_result(r)
    return all_results


def print_table(results: list[Result]) -> None:
    banner("Final results")
    width_id = max((len(r.test_id) for r in results), default=20)
    width_name = max((len(r.name) for r in results), default=30)
    print(f"  {'Test':<{width_id}}  {'Name':<{width_name}}  Result")
    print(f"  {'-' * width_id}  {'-' * width_name}  ------")
    n_pass = n_fail = n_skip = 0
    for r in results:
        if r.passed is True:
            colour, label = Fore.GREEN, "PASS"; n_pass += 1
        elif r.passed is False:
            colour, label = Fore.RED, "FAIL"; n_fail += 1
        else:
            colour, label = Fore.YELLOW, "SKIP"; n_skip += 1
        print(f"  {r.test_id:<{width_id}}  {r.name:<{width_name}}  {colour}{label}{Style.RESET_ALL}")
    print()
    print(f"  Total: {len(results)}   Pass: {n_pass}   Fail: {n_fail}   Skip: {n_skip}")


def main() -> None:
    env = load_env()
    verify_target(env["APP_BASE_URL"])
    run_seed_script()
    results = run_tests()
    summary_path, evidence_path = write_outputs(results, HERE, env["APP_BASE_URL"])
    print_table(results)
    print()
    print(f"  Wrote summary:  {summary_path}")
    print(f"  Wrote evidence: {evidence_path}")
    # Non-zero exit only if an actual test failure (not skip)
    sys.exit(1 if any(r.passed is False for r in results) else 0)


if __name__ == "__main__":
    main()
