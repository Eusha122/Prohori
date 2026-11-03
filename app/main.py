"""Prohori web app (local prototype): JSON API over data/prohori.duckdb + a static front end.

Run:  .venv/Scripts/python -m uvicorn app.main:app --port 8000
Stop the app before re-running the pipeline scripts (they need write access to the DB).
"""
from pathlib import Path

import duckdb
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "prohori.duckdb"
STATIC = Path(__file__).resolve().parent / "static"

# Thresholds for the rule-based flags shown to users (kept in sync with build_features.py).
DOMINANCE_SHARE = 0.40
MIN_OFFICE_CONTRACTS = 20
DIRECT_SHARE = 0.30
AMBIGUOUS_DISTRICTS = 9

app = FastAPI(title="Prohori")
_db = duckdb.connect(str(DB_PATH), read_only=True)


def query(sql: str, params=None) -> list[dict]:
    cur = _db.cursor()
    rel = cur.execute(sql, params or [])
    cols = [d[0] for d in rel.description]
    return [dict(zip(cols, row)) for row in rel.fetchall()]


def company_flags(c: dict, top_offices: list[dict]) -> list[dict]:
    """Plain-language risk patterns for one company. Patterns for review, never accusations."""
    flags = []
    if c["n_debarments"]:
        flags.append({
            "level": "high",
            "en": f"Officially debarred by {c['debarred_by'].split(',')[0].strip()} "
                  f"({c['first_debar_from']:%d %b %Y} – {c['last_debar_to']:%d %b %Y}).",
            "bn": "সরকার এই প্রতিষ্ঠানকে নিষিদ্ধ করেছে।",
            # e-GP truncates long reasons and appends its own "... more" link text.
            "detail": (c["debar_reason"] or "").removesuffix("more").rstrip(" .") + "…",
        })
    for o in top_offices:
        if o["share_n"] >= DOMINANCE_SHARE and o["office_n"] >= MIN_OFFICE_CONTRACTS:
            flags.append({
                "level": "medium",
                "en": f"Wins {o['share_n']:.0%} of all contracts at {o['procuring_entity']} "
                      f"({o['n']} of {o['office_n']}).",
                "bn": "একই অফিসে বেশিরভাগ কাজ এই প্রতিষ্ঠান পায়।",
            })
    if c["share_direct"] >= DIRECT_SHARE and c["n_contracts"] >= 5:
        flags.append({
            "level": "medium",
            "en": f"{c['share_direct']:.0%} of its contracts used direct or single-source buying "
                  f"(no open competition).",
            "bn": "অনেক কাজ প্রতিযোগিতা ছাড়াই দেওয়া হয়েছে।",
        })
    if c["name_may_be_shared"]:
        flags.append({
            "level": "info",
            "en": f"This name appears in {c['n_districts']} districts — it may belong to several "
                  f"different firms. Verify by address before drawing conclusions.",
            "bn": "একই নামে একাধিক প্রতিষ্ঠান থাকতে পারে।",
        })
    return flags


@app.get("/api/stats")
def stats():
    s = query("""
        SELECT count(*) AS contracts, sum(value_bdt) AS value_bdt,
               count(DISTINCT winner_key) AS companies, count(DISTINCT procuring_entity) AS offices,
               min(signed_date) AS first_date, max(signed_date) AS last_date
        FROM contracts""")[0]
    s["dominant_companies"] = query(
        "SELECT count(*) AS n FROM company_summary WHERE n_dominated_offices > 0")[0]["n"]
    s["debarred_found"] = query(
        "SELECT count(*) AS n FROM company_summary WHERE n_debarments > 0")[0]["n"]
    return s


@app.get("/api/search")
def search(q: str = Query(min_length=2)):
    like = f"%{q.lower()}%"
    companies = query("""
        SELECT winner_key AS key, name, n_contracts, value_bdt, n_districts, n_debarments,
               n_dominated_offices
        FROM company_summary WHERE winner_key LIKE ? OR lower(name) LIKE ?
        ORDER BY value_bdt DESC NULLS LAST LIMIT 20""", [like, like])
    offices = query("""
        SELECT procuring_entity AS name, district, n_contracts, value_bdt, top_share_n
        FROM office_summary WHERE lower(procuring_entity) LIKE ?
        ORDER BY n_contracts DESC LIMIT 10""", [like])
    return {"companies": companies, "offices": offices}


@app.get("/api/company")
def company(key: str):
    rows = query("SELECT * FROM company_summary WHERE winner_key = ?", [key])
    if not rows:
        raise HTTPException(404, "company not found")
    c = rows[0]
    top_offices = query("""
        SELECT ow.procuring_entity, ow.n, ow.value_bdt, ow.share_n, ow.office_n, os.district
        FROM office_winner ow JOIN office_summary os USING (procuring_entity)
        WHERE ow.winner_key = ? ORDER BY ow.n DESC LIMIT 10""", [key])
    by_year = query("""
        SELECT year(signed_date) AS year, count(*) AS n, sum(value_bdt) AS value_bdt
        FROM contracts WHERE winner_key = ? GROUP BY 1 ORDER BY 1""", [key])
    recent = query("""
        SELECT signed_date, title, procuring_entity, district, method, value_bdt, tender_id, pkg_lot_id
        FROM contracts WHERE winner_key = ? ORDER BY signed_date DESC LIMIT 25""", [key])
    return {"company": c, "flags": company_flags(c, top_offices), "top_offices": top_offices,
            "by_year": by_year, "recent": recent}


@app.get("/api/office")
def office(name: str):
    rows = query("SELECT * FROM office_summary WHERE procuring_entity = ?", [name])
    if not rows:
        raise HTTPException(404, "office not found")
    winners = query("""
        SELECT ow.winner_key AS key, cs.name, ow.n, ow.value_bdt, ow.share_n, cs.n_debarments
        FROM office_winner ow JOIN company_summary cs USING (winner_key)
        WHERE ow.procuring_entity = ? ORDER BY ow.n DESC LIMIT 15""", [name])
    recent = query("""
        SELECT signed_date, title, winner_clean AS winner, winner_key, method, value_bdt
        FROM contracts WHERE procuring_entity = ? ORDER BY signed_date DESC LIMIT 25""", [name])
    return {"office": rows[0], "winners": winners, "recent": recent}


@app.get("/api/patterns")
def patterns(limit: int = 50):
    """Offices where a single company wins an unusually large share of contracts."""
    return query("""
        SELECT os.procuring_entity AS office, os.district, os.ministry, os.n_contracts,
               os.value_bdt, os.top_share_n, os.top_winner_key AS winner_key, cs.name AS winner,
               cs.n_debarments
        FROM office_summary os JOIN company_summary cs ON cs.winner_key = os.top_winner_key
        WHERE os.n_contracts >= 30 AND os.top_share_n >= ?
        ORDER BY os.top_share_n DESC, os.n_contracts DESC LIMIT ?""", [DOMINANCE_SHARE, limit])


@app.get("/api/debarred")
def debarred(limit: int = 200):
    """Officially debarred firms that also appear as contract winners."""
    return query("""
        SELECT winner_key AS key, name, n_contracts, value_bdt, n_districts, first_debar_from,
               last_debar_to, debarred_by, name_may_be_shared
        FROM company_summary WHERE n_debarments > 0
        ORDER BY value_bdt DESC NULLS LAST LIMIT ?""", [limit])


@app.get("/api/largest")
def largest(limit: int = 50):
    return query("""
        SELECT signed_date, title, procuring_entity, district, winner_clean AS winner, winner_key,
               method, value_bdt, tender_id, pkg_lot_id
        FROM contracts WHERE value_bdt IS NOT NULL ORDER BY value_bdt DESC LIMIT ?""", [limit])


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
