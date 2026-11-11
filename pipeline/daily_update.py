"""Nightly data update. Runs on the server every day at 03:00 Bangladesh time (systemd timer).

1. Collect the newest contract-award pages from e-GP (newest first) and the full debarment list,
   with the same polite collectors used to build the database (Node + Playwright).
2. Add only contracts that are not in the database yet; replace the debarment table.
3. Re-run debarment matching and the summary tables. Once a week (Sunday, or with --rescore)
   re-score every active firm with the SAVED model (no retraining: same tested model).
4. All work happens on a copy of the database. The copy is swapped in at the end and the web
   app is restarted by systemd (a few seconds). If anything fails, the live site keeps
   yesterday's data and tomorrow's run tries again.

Usage:  python pipeline/daily_update.py [--rescore] [--pages N] [--skip-collect]
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import duckdb  # noqa: E402

import build_db  # noqa: E402
import build_features  # noqa: E402
import match_debarred  # noqa: E402
import train_model  # noqa: E402

LIVE = ROOT / "data" / "prohori.duckdb"
NEXT = ROOT / "data" / "prohori.next.duckdb"
NOA_DIR = ROOT / "data" / "raw" / "noa"
DEBAR_FILE = ROOT / "data" / "raw" / "debarment" / "debarment.jsonl"
STATUS = ROOT / "data" / "last_update.json"


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def log(msg):
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}", flush=True)


def run(cmd, timeout, tries=3):
    """Run a collector; on failure (e.g. a short network or DNS glitch) wait 2 minutes and try again."""
    for attempt in range(1, tries + 1):
        log(f"run (try {attempt}/{tries}): " + " ".join(cmd))
        try:
            if subprocess.run(cmd, cwd=ROOT / "collector", timeout=timeout).returncode == 0:
                return True
        except subprocess.TimeoutExpired:
            log("timed out")
        if attempt < tries:
            time.sleep(120)
    return False


def collect(pages: int) -> list[dict]:
    """Fetch the newest `pages` award pages (10 rows each) and refresh the debarment list."""
    NOA_DIR.mkdir(parents=True, exist_ok=True)
    for f in glob.glob(str(NOA_DIR / "noa_daily_*.jsonl")) + [str(NOA_DIR / "pages_done_daily.txt")]:
        if os.path.exists(f):
            os.remove(f)
    ok = run(["node", "collect_noa.js", "--from", "1", "--to", str(pages), "--delay-ms", "1500",
              "--worker", "daily"], timeout=60 * 60)
    rows = []
    for f in sorted(glob.glob(str(NOA_DIR / "noa_daily_*.jsonl"))):
        with open(f, encoding="utf8") as fh:
            rows += [json.loads(line) for line in fh if line.strip()]
    log(f"award pages: {'ok' if ok else 'stopped early'}, {len(rows):,} rows read")

    # Debarment list: keep yesterday's file if today's download looks broken.
    backup = DEBAR_FILE.with_suffix(".jsonl.bak")
    if DEBAR_FILE.exists():
        shutil.copy2(DEBAR_FILE, backup)
    ok = run(["node", "collect_debarment.js"], timeout=30 * 60)
    n = sum(1 for _ in open(DEBAR_FILE, encoding="utf8")) if DEBAR_FILE.exists() else 0
    if (not ok or n < 500) and backup.exists():
        shutil.copy2(backup, DEBAR_FILE)
        log(f"debarment download looked wrong ({n} rows); kept yesterday's list")
    else:
        log(f"debarment list: {n:,} rows")
    return rows


def main():
    t0 = time.time()
    rows = [] if "--skip-collect" in sys.argv else collect(int(arg("--pages", os.getenv("DAILY_PAGES", "60"))))

    shutil.copy2(LIVE, NEXT)
    for m in (build_db, match_debarred, build_features, train_model):
        m.DB_PATH = NEXT

    con = duckdb.connect(str(NEXT))
    before = con.execute("SELECT count(*) FROM contracts").fetchall()[0][0]
    if rows:
        con.register("new_df", build_db.to_contracts(rows))
        con.execute("""
            INSERT INTO contracts
            SELECT n.* FROM new_df n
            WHERE NOT EXISTS (SELECT 1 FROM contracts c
                              WHERE c.pkg_lot_id IS NOT DISTINCT FROM n.pkg_lot_id
                                AND c.tender_id IS NOT DISTINCT FROM n.tender_id
                                AND c.winner = n.winner)""").fetchall()
    after = con.execute("SELECT count(*) FROM contracts").fetchall()[0][0]
    con.register("debar_df", build_db.load_debarments())
    con.execute("CREATE OR REPLACE TABLE debarments AS SELECT * FROM debar_df").fetchall()
    n_debar = con.execute("SELECT count(*) FROM debarments").fetchall()[0][0]
    con.close()
    log(f"contracts: {before:,} -> {after:,} (+{after - before:,})")

    match_debarred.main()
    build_features.main()
    rescored = "--rescore" in sys.argv or date.today().weekday() == 6
    if rescored:
        train_model.score_only()

    os.replace(NEXT, LIVE)
    STATUS.write_text(json.dumps({
        "updated": datetime.now().isoformat(timespec="seconds"), "contracts": after, "added": after - before,
        "debarments": n_debar, "rescored": rescored, "seconds": round(time.time() - t0),
    }), encoding="utf8")
    log(f"done in {time.time() - t0:.0f}s; new database is live after the app restart")


if __name__ == "__main__":
    main()
