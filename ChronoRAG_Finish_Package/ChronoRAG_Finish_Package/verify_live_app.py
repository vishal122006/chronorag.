"""Check whether the locally running ChronoRAG Streamlit server responds.

Usage:
    python verify_live_app.py
    python verify_live_app.py http://localhost:8501

This uses only Python's standard library and should run while the app is open.
It is an HTTP health check, not a full interactive browser automation test.
"""
from __future__ import annotations
import sys
import time
from urllib.error import URLError, HTTPError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


def fetch(url: str, timeout: float = 3.0) -> tuple[int, str]:
    request = Request(url, headers={"User-Agent": "ChronoRAG-Live-Health-Check/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return int(response.status), response.read(300_000).decode("utf-8", errors="replace")


def main() -> int:
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8501").rstrip("/")
    checks: list[tuple[bool, str]] = []

    try:
        status, health = fetch(urljoin(base + "/", "_stcore/health"))
        checks.append((status == 200 and health.strip().lower() in {"ok", "healthy"},
                       f"Streamlit health endpoint returned HTTP {status} and body {health.strip()[:80]!r}"))
    except (URLError, HTTPError, TimeoutError, OSError) as exc:
        checks.append((False, f"Health endpoint could not be reached: {exc}"))

    try:
        status, html = fetch(base + "/")
        okay = status == 200 and ("streamlit" in html.lower() or "stroot" in html.lower())
        checks.append((okay, f"App root returned HTTP {status}; Streamlit page shell detected={okay}"))
    except (URLError, HTTPError, TimeoutError, OSError) as exc:
        checks.append((False, f"App root could not be reached: {exc}"))

    print("ChronoRAG Live App HTTP Verification")
    print("====================================")
    for passed, message in checks:
        print(f"{'PASS' if passed else 'FAIL'}: {message}")
    good = sum(p for p, _ in checks)
    print(f"\nTOTAL: {good}/{len(checks)} live HTTP checks passed.")
    if good != len(checks):
        print("\nMake sure Install_and_Run.bat is still running and open the same local URL.")
        print("If your app uses another port, run: python verify_live_app.py http://localhost:PORT")
        return 1
    print(f"Live server is responding at {base}. Keep its terminal open while using the app.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
