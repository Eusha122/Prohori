"""Prohori web app (local prototype): JSON API over data/prohori.duckdb + a static front end.

Run:  .venv/Scripts/python -m uvicorn app.main:app --port 8000
Stop the app before re-running the pipeline scripts (they need write access to the DB).
"""
import json
import os
import secrets
from pathlib import Path

import duckdb
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import pandas as pd

from fastapi.responses import StreamingResponse

from app.agent import Investigator
from app.ai import PAGE_ABOUT, AIUnavailable, NovaAssistant, fact_sheet, office_sheet, page_sheet
from app.growth import Growth
from app.law import LawIndex
from app.risk import RiskIndex, fmt
from pipeline.geo import canonical_district, division_of

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
RISK = RiskIndex(_db)
AI = NovaAssistant()
GROWTH = Growth()

# e-GP uses old and new spellings of district names (Jessore/Jashore, Bogra/Bogura). Map each raw name
# to one canonical district and its division; registered on every cursor as the view "dmap".
_raw_districts = [r[0] for r in _db.execute("SELECT DISTINCT district FROM contracts").fetchall()]
DMAP = pd.DataFrame([(r, canonical_district(r) or r, division_of(r) or "") for r in _raw_districts],
                    columns=["raw", "district", "division"])

# Facts from contract detail pages (bidder counts etc.), downloaded for a sample of firms.
DETAIL_PATH = ROOT / "data" / "detail_contracts.parquet"
HAS_DETAIL = DETAIL_PATH.exists()
DETAIL = f"read_parquet('{DETAIL_PATH.as_posix()}')"


@app.middleware("http")
async def revalidate_static(request, call_next):
    """Make browsers re-check the page and static files on every load, so design/logo
    updates show up without a hard refresh (unchanged files still return a cheap 304)."""
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response


def query(sql: str, params=None) -> list[dict]:
    cur = _db.cursor()
    cur.register("dmap", DMAP)
    rel = cur.execute(sql, params or [])
    cols = [d[0] for d in rel.description]
    return [dict(zip(cols, row)) for row in rel.fetchall()]


BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


def bn(x) -> str:
    """Write numbers with Bangla digits for the Bangla version of the site."""
    return str(x).translate(BN_DIGITS)


def company_flags(c: dict, top_offices: list[dict]) -> list[dict]:
    """Plain-language risk patterns for one company. Patterns for review, never accusations."""
    flags = []
    if c["n_debarments"]:
        flags.append({
            "level": "high",
            "en": f"Officially debarred by {c['debarred_by'].split(',')[0].strip()} "
                  f"({c['first_debar_from']:%d %b %Y} – {c['last_debar_to']:%d %b %Y}).",
            "bn": f"{c['debarred_by'].split(',')[0].strip()} এই প্রতিষ্ঠানকে সরকারিভাবে নিষিদ্ধ করেছে "
                  f"({bn(c['first_debar_from'].strftime('%d/%m/%Y'))} – {bn(c['last_debar_to'].strftime('%d/%m/%Y'))})।",
            # e-GP truncates long reasons and appends its own "... more" link text.
            "detail": (c["debar_reason"] or "").removesuffix("more").rstrip(" .") + "…",
        })
    for o in top_offices:
        if o["share_n"] >= DOMINANCE_SHARE and o["office_n"] >= MIN_OFFICE_CONTRACTS:
            flags.append({
                "level": "medium",
                "en": f"Wins {o['share_n']:.0%} of all contracts at {o['procuring_entity']} "
                      f"({o['n']} of {o['office_n']}).",
                "bn": f"{o['procuring_entity']}-এর সব চুক্তির {bn(round(o['share_n'] * 100))}% এই প্রতিষ্ঠান পেয়েছে "
                      f"({bn(o['n'])}টি / {bn(o['office_n'])}টি)।",
            })
    if c["share_direct"] >= DIRECT_SHARE and c["n_contracts"] >= 5:
        flags.append({
            "level": "medium",
            "en": f"{c['share_direct']:.0%} of its contracts used direct or single-source buying "
                  f"(no open competition).",
            "bn": f"এর {bn(round(c['share_direct'] * 100))}% চুক্তি সরাসরি বা একক উৎসে ক্রয়ে দেওয়া হয়েছে "
                  f"(উন্মুক্ত প্রতিযোগিতা ছাড়া)।",
        })
    if c["name_may_be_shared"]:
        flags.append({
            "level": "info",
            "en": f"This name appears in {c['n_districts']} districts — it may belong to several "
                  f"different firms. Verify by address before drawing conclusions.",
            "bn": f"এই নাম {bn(c['n_districts'])}টি জেলায় দেখা যায় — এটি একাধিক আলাদা প্রতিষ্ঠানের হতে পারে। "
                  f"সিদ্ধান্তের আগে ঠিকানা মিলিয়ে নিন।",
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
    s["risk"] = RISK.summary()
    # Set by the nightly update on the server (pipeline/daily_update.py).
    status = ROOT / "data" / "last_update.json"
    s["data_updated"] = json.loads(status.read_text(encoding="utf8"))["updated"] if status.exists() else None
    m = RISK.metrics["main_test"]
    s["model"] = {"auc": m["roc_auc"], "caught_share": m["caught_in_advance"]["share"],
                  "months_early": m["caught_in_advance"]["median_months_before_ban"]}
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
    bids = {}
    if HAS_DETAIL:
        bids = query(f"""
            SELECT count(*) AS pages, count(d.received) AS with_bids, median(d.received) AS median_received,
                   sum(d.single_bid) AS single_bid, sum(d.sign_late) AS sign_late, sum(d.ps_late) AS ps_late
            FROM contracts c JOIN {DETAIL} d ON d.tender_id = c.tender_id AND d.pkg_lot_id = c.pkg_lot_id
            WHERE c.winner_key = ?""", [key])[0]
        got = {(r["tender_id"], r["pkg_lot_id"]): r for r in query(f"""
            SELECT d.tender_id, d.pkg_lot_id, d.received, d.sold FROM contracts c
            JOIN {DETAIL} d ON d.tender_id = c.tender_id AND d.pkg_lot_id = c.pkg_lot_id
            WHERE c.winner_key = ?""", [key])}
        for r in recent:
            g = got.get((r["tender_id"], r["pkg_lot_id"]))
            r["received"] = g["received"] if g else None
    return {"company": c, "flags": company_flags(c, top_offices), "top_offices": top_offices,
            "by_year": by_year, "recent": recent, "risk": RISK.for_company(key), "bids": bids,
            "scored": RISK.n}


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


@app.get("/api/watchlist")
def watchlist(view: str = "overall", division: str | None = None, limit: int = Query(100, le=500)):
    """Firms the AI model ranks highest for review (not accusations)."""
    rows = RISK.watchlist(view, division or None, limit)
    keys = [r["winner_key"] for r in rows]
    if keys:
        deb = {r["k"] for r in query(
            f"SELECT winner_key AS k FROM company_summary WHERE n_debarments > 0 AND winner_key IN "
            f"({','.join('?' * len(keys))})", keys)}
        for r in rows:
            r["debarred_elsewhere"] = r["winner_key"] in deb
    return {"rows": rows, **RISK.summary()}


@app.get("/api/model")
def model_report():
    return RISK.model_report()


def client_ip(request: Request) -> str:
    # Behind a proxy (when deployed) the real visitor address is the first X-Forwarded-For entry.
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?")


def page_rows(page: str) -> list[str]:
    """The top rows a list page shows, as short lines for the AI fact sheet."""
    tk = lambda v: fmt(v, "tk")  # noqa: E731
    if page == "watchlist":
        return [f"- {r['name']} ({r['division']} division): priority {r['band_label']}, top {r['top_pct']}% "
                f"overall, top {r['top_pct_size']}% among similar-size firms, {r['n_contracts']} contracts; reasons: "
                + "; ".join(y["label"] for y in r["reasons"]) for r in RISK.watchlist("overall", None, 15)]
    if page in ("patterns", "home"):
        return [f"- {r['office']} ({r['district']}): {r['winner']} won {r['top_share_n']:.0%} of "
                f"{r['n_contracts']} contracts" + (" [debarred name]" if r["n_debarments"] else "")
                for r in patterns(15 if page == "patterns" else 5)]
    if page == "debarred":
        return [f"- {r['name']}: {r['n_contracts']} contracts, {tk(r['value_bdt'])}; debarred "
                f"{r['first_debar_from']:%d %b %Y} to {r['last_debar_to']:%d %b %Y} by "
                f"{(r['debarred_by'] or '').split(',')[0]}" for r in debarred(15)]
    if page == "largest":
        return [f"- {r['signed_date']:%d %b %Y}: {(r['title'] or '')[:90]} | {r['winner']} | {r['procuring_entity']} "
                f"| {tk(r['value_bdt'])}" for r in largest(12)]
    return []


def district_rows(name: str) -> list[str]:
    """One district's numbers as short lines for the AI fact sheet."""
    d = district(name)
    s, tk = d["summary"], (lambda v: fmt(v, "tk"))
    out = [f"- District: {name} ({d['division']} division). {s['n']:,} contracts worth {tk(s['value_bdt'])} from "
           f"{s['offices']} government offices, won by {s['winners']:,} companies; last 12 months: {s['n_12m']:,} "
           f"contracts worth {tk(s['value_12m'])}."]
    out += [f"- Year {y['year']}: {y['n']} contracts, {tk(y['value_bdt'])}" for y in d["by_year"][-6:]]
    out += [f"- Top winner: {w['name']}: {w['n']} contracts, {tk(w['value_bdt'])}"
            + (f", AI review priority {w['band_label']}" if w["band_label"] else "")
            + (" [name on debarment list]" if w["n_debarments"] else "") for w in d["winners"][:10]]
    out += [f"- Office where one company wins most: {o['name']}: {o['top_winner']} won {o['top_share_n']:.0%} of "
            f"{o['n_contracts']} contracts" for o in d["dominated"]]
    out += [f"- Officially debarred firm that won contracts here: {x['name']}: {x['n']} contracts, "
            f"{tk(x['value_bdt'])}" for x in d["debarred"]]
    out += [f"- Large recent contract: {x['signed_date']:%d %b %Y}: {(x['title'] or '')[:120]} | {x['winner']} | "
            f"{x['procuring_entity']} | {tk(x['value_bdt'])}" for x in d["biggest"]]
    return out


def ai_context(ctx: str, key: str):
    """Returns (kind, cache id, facts function) for the page the visitor is on."""
    if ctx == "company":
        def facts():
            r = company(key)
            return fact_sheet(r, RISK.metrics), r["company"]["name"]
        return "company", f"company:{key}", facts
    if ctx in ("report", "brief"):
        return ai_context("company", key)
    if ctx == "office":
        return "office", f"office:{key}", lambda: (office_sheet(office(key)), key)
    if ctx == "district":
        return "page", f"page:district:{key}", lambda: (
            page_sheet("district", stats(), RISK.metrics, district_rows(key)), None)
    page = ctx if ctx in PAGE_ABOUT else "home"
    return "page", f"page:{page}", lambda: (page_sheet(page, stats(), RISK.metrics, page_rows(page)), None)


@app.get("/api/explain")
def explain(request: Request, ctx: str = "company", key: str = "", lang: str = "bn"):
    """Plain-language explanation of the current page (company, office or list) in Bangla or English, by Amazon Nova."""
    kind, cid, facts = ai_context(ctx, key)
    try:
        return AI.explain(kind, cid, facts, client_ip(request), "en" if lang == "en" else "bn")
    except AIUnavailable as e:
        raise HTTPException(503, str(e))


class Question(BaseModel):
    question: str
    ctx: str = "company"
    key: str = ""
    history: list[dict] = []        # earlier [{q, a}] of this chat, newest last


@app.post("/api/ask")
def ask(q: Question, request: Request):
    """Answer a citizen's question about the current page, using only that page's facts."""
    kind, cid, facts = ai_context(q.ctx, q.key)
    try:
        return AI.ask(kind, cid, facts, q.question, client_ip(request), q.history)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except AIUnavailable as e:
        raise HTTPException(503, str(e))


@app.get("/api/districts")
def districts():
    """All 64 districts with contract counts, for the Probashi (diaspora) district picker."""
    return query("""
        SELECT m.district, m.division, count(*) AS n, sum(c.value_bdt) AS value_bdt,
               count(*) FILTER (WHERE c.signed_date >= current_date - INTERVAL 365 DAY) AS n_12m
        FROM contracts c JOIN dmap m ON m.raw = c.district
        GROUP BY 1, 2 ORDER BY 1""")


@app.get("/api/district")
def district(name: str):
    """What is being built in one home district: money, who wins, offices to watch, debarred winners."""
    raws = DMAP.loc[DMAP["district"] == name, "raw"].tolist()
    if not raws:
        raise HTTPException(404, "district not found")
    ph = ",".join("?" * len(raws))
    s = query(f"""
        SELECT count(*) AS n, sum(value_bdt) AS value_bdt, count(DISTINCT procuring_entity) AS offices,
               count(DISTINCT winner_key) AS winners, min(signed_date) AS first_date, max(signed_date) AS last_date,
               count(*) FILTER (WHERE signed_date >= current_date - INTERVAL 365 DAY) AS n_12m,
               sum(value_bdt) FILTER (WHERE signed_date >= current_date - INTERVAL 365 DAY) AS value_12m
        FROM contracts WHERE district IN ({ph})""", raws)[0]
    division = division_of(name)
    by_year = query(f"""SELECT year(signed_date) AS year, count(*) AS n, sum(value_bdt) AS value_bdt
        FROM contracts WHERE district IN ({ph}) GROUP BY 1 ORDER BY 1""", raws)
    winners = query(f"""
        SELECT c.winner_key AS key, cs.name, count(*) AS n, sum(c.value_bdt) AS value_bdt, cs.n_debarments
        FROM contracts c JOIN company_summary cs USING (winner_key)
        WHERE c.district IN ({ph}) GROUP BY 1, 2, 5 ORDER BY 4 DESC NULLS LAST LIMIT 15""", raws)
    for w in winners:
        r = [x for x in RISK.for_company(w["key"]) if x["division"] == division]
        w["band"], w["band_label"] = (r[0]["band"], r[0]["band_label"]) if r else (None, None)
    offices = query(f"""
        SELECT os.procuring_entity AS name, os.n_contracts, os.value_bdt, os.top_share_n, cs.name AS top_winner,
               os.top_winner_key AS top_key
        FROM office_summary os LEFT JOIN company_summary cs ON cs.winner_key = os.top_winner_key
        WHERE os.district IN ({ph}) ORDER BY os.value_bdt DESC NULLS LAST LIMIT 12""", raws)
    dominated = [o for o in query(f"""
        SELECT os.procuring_entity AS name, os.n_contracts, os.top_share_n, cs.name AS top_winner,
               os.top_winner_key AS top_key, cs.n_debarments
        FROM office_summary os JOIN company_summary cs ON cs.winner_key = os.top_winner_key
        WHERE os.district IN ({ph}) AND os.n_contracts >= 20 AND os.top_share_n >= ?
        ORDER BY os.top_share_n DESC LIMIT 10""", raws + [DOMINANCE_SHARE])]
    debarred_here = query(f"""
        SELECT c.winner_key AS key, cs.name, count(*) AS n, sum(c.value_bdt) AS value_bdt,
               cs.first_debar_from, cs.last_debar_to, cs.name_may_be_shared
        FROM contracts c JOIN company_summary cs USING (winner_key)
        WHERE c.district IN ({ph}) AND cs.n_debarments > 0
        GROUP BY 1, 2, 5, 6, 7 ORDER BY 4 DESC NULLS LAST LIMIT 10""", raws)
    biggest = query(f"""
        SELECT signed_date, title, procuring_entity, winner_clean AS winner, winner_key, method, value_bdt,
               tender_id, pkg_lot_id
        FROM contracts WHERE district IN ({ph}) AND signed_date >= current_date - INTERVAL 3 YEAR
        ORDER BY value_bdt DESC NULLS LAST LIMIT 10""", raws)
    recent = query(f"""
        SELECT signed_date, title, procuring_entity, winner_clean AS winner, winner_key, method, value_bdt,
               tender_id, pkg_lot_id
        FROM contracts WHERE district IN ({ph}) ORDER BY signed_date DESC LIMIT 15""", raws)
    return {"district": name, "division": division, "summary": s, "by_year": by_year, "winners": winners,
            "offices": offices, "dominated": dominated, "debarred": debarred_here, "biggest": biggest,
            "recent": recent}


@app.get("/api/report")
def contractor_report(key: str):
    """Contractor Check Report: the due-diligence page a bank or finance company would buy (Lender Check)."""
    r = company(key)
    r["methods"] = query("""SELECT method, count(*) AS n, sum(value_bdt) AS value_bdt FROM contracts
        WHERE winner_key = ? GROUP BY 1 ORDER BY 2 DESC""", [key])
    r["last3"] = query("""SELECT count(*) AS n, sum(value_bdt) AS value_bdt, count(DISTINCT procuring_entity) AS offices
        FROM contracts WHERE winner_key = ? AND signed_date >= current_date - INTERVAL 3 YEAR""", [key])[0]
    r["ministries"] = query("""SELECT ministry, count(*) AS n FROM contracts WHERE winner_key = ?
        GROUP BY 1 ORDER BY 2 DESC LIMIT 5""", [key])
    r["data_through"] = query("SELECT max(signed_date) AS d FROM contracts")[0]["d"]
    return r


LAW = LawIndex(client_factory=AI.client)


class AgentData:
    """What the investigator agent's tools may read: the same data the public pages show, plus the law."""
    law = LAW
    query = staticmethod(query)
    company = staticmethod(company)
    office = staticmethod(office)
    _ban_names = None

    @staticmethod
    def metrics():
        return RISK.metrics

    @classmethod
    def ban_names(cls):
        if cls._ban_names is None:
            cls._ban_names = [r["n"] for r in query("SELECT DISTINCT lower(company) AS n FROM debarments")]
        return cls._ban_names


INVESTIGATOR = Investigator(AI, AgentData)


@app.get("/api/law")
def law_search(q: str = Query(min_length=3, max_length=200)):
    """Search the procurement law (Rules 2025, Act 2006 and amendments); each result links to the official PDF page."""
    return LAW.search(q, k=5)


@app.get("/api/brief")
def brief(request: Request, key: str, lang: str = "en"):
    """Investigator agent: streams each tool call as it happens, then the finished, checked brief (server-sent events)."""
    if not query("SELECT 1 AS x FROM company_summary WHERE winner_key = ?", [key]):
        raise HTTPException(404, "company not found")
    status = ROOT / "data" / "last_update.json"
    data_date = json.loads(status.read_text(encoding="utf8"))["updated"][:10] if status.exists() else "local"
    ip = client_ip(request)

    def events():
        try:
            for ev in INVESTIGATOR.stream(key, lang, ip, data_date):
                yield f"data: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n"
        except AIUnavailable as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        except Exception:
            import traceback
            traceback.print_exc()           # goes to the server log
            yield f"data: {json.dumps({'type': 'error', 'message': 'The investigator stopped because of an error. Please try again.'})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


class Signup(BaseModel):
    plan: str
    role: str
    contact: str
    name: str = ""
    place: str = ""
    abroad: bool = False
    target: str = ""
    price_variant: str = ""
    note: str = ""


@app.post("/api/signup")
def signup(s: Signup, request: Request):
    """Waitlist for planned plans. Nothing is sold and no money is taken."""
    try:
        return GROWTH.signup(s.model_dump(), client_ip(request))
    except ValueError as e:
        raise HTTPException(400, str(e))


class Event(BaseModel):
    event: str
    page: str = ""
    vid: str = ""
    abroad: bool = False


@app.post("/api/track")
def track(e: Event):
    """Anonymous usage counter: no cookies, no IP addresses stored."""
    GROWTH.track(e.model_dump())
    return {"ok": True}


ADMIN_KEY = os.getenv("PROHORI_ADMIN_KEY", "")


@app.get("/api/numbers")
def numbers(request: Request):
    """Usage and waitlist numbers: PRIVATE (team only). Needs the admin key from .env; off if no key is set."""
    if not ADMIN_KEY or not secrets.compare_digest(request.headers.get("x-admin-key", ""), ADMIN_KEY):
        raise HTTPException(403, "This page is private.")
    return GROWTH.numbers()


@app.api_route("/", methods=["GET", "HEAD"])  # HEAD too: link checkers (e.g. the hackathon's) use it
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
