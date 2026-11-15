"""Request every URL in data/sources.csv once and record the HTTP status (README link audit, B20.1 item 7)."""
import datetime as dt

import pandas as pd
import requests

from src.paths import DATA, REPORTS

UA = {"User-Agent": "Mozilla/5.0 (RotateWise link audit)"}


def check(url):
    try:
        r = requests.get(url, headers=UA, timeout=60, allow_redirects=True, stream=True)
        r.close()
        return "OK" if r.status_code < 400 else f"HTTP {r.status_code}"
    except Exception as e:
        return f"FAILED ({type(e).__name__})"


def main():
    s = pd.read_csv(DATA / "sources.csv")
    today = dt.date.today().isoformat()
    rows = [{"id": r.id, "url": r.url, "status": check(r.url), "checked": today} for r in s.itertuples()]
    out = pd.DataFrame(rows)
    out.to_csv(REPORTS / "link_audit.csv", index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
