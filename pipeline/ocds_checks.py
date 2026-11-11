"""Run Prohori's rule-based checks on ANY country's OCDS data, the same code for every country.

    python pipeline/ocds_checks.py            # all datasets below -> app/intl/checks.json

Bangladesh is checked from Prohori's own OCDS export (pipeline/export_ocds.py), so the Bangladesh numbers go
through exactly the same code as the other countries. Data for other countries comes from the Open Contracting
Partnership's data registry (data.open-contracting.org), downloaded to data/intl/<id>/full.jsonl.gz.

Checks (each one runs only when the data has the fields it needs; otherwise it says "not available"):
  dominance      buying offices with 30+ awards where ONE supplier won 40% or more of them
  direct         share of tenders using the "direct" method (no competition), OCDS codelist values only
  single_bid     share of tenders that received exactly one tender
  short_window   share of open tenders whose bidding window was shorter than 7 days (skipped, and reported as a
                 data-quality problem, when over 20% of the dates are impossible: end on or before the start day)
  concentration  share of all award value won by the top 5% of suppliers (main currency only)
These are patterns for review, not findings of wrongdoing. The AI risk model is NOT applied to other countries:
it learned from Bangladesh's debarment list, and there is no comparable label elsewhere in these datasets.
"""
import gzip
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "app" / "intl" / "checks.json"
REGISTRY = "https://data.open-contracting.org/en/publication/"

DATASETS = [
    {"id": "bd", "country": "Bangladesh", "country_bn": "বাংলাদেশ",
     "source": "Bangladesh e-GP award notices (Prohori's OCDS export)", "url": "https://www.eprocure.gov.bd",
     "files": sorted((ROOT / "data" / "ocds").glob("bd-egp-*.json.gz")),
     "note": "Tenders-received counts exist only for the ~28,000 contracts whose detail pages Prohori read "
             "(not a random sample)."},
    {"id": "ke", "country": "Kenya", "country_bn": "কেনিয়া",
     "source": "Public Procurement Regulatory Authority (PPRA)", "url": REGISTRY + "147",
     "files": [ROOT / "data" / "intl" / "kenya" / "full.jsonl.gz"]},
    {"id": "np", "country": "Nepal", "country_bn": "নেপাল",
     "source": "Public Procurement Monitoring Office (PPMO), from Nepal's e-GP system", "url": REGISTRY + "36",
     "files": [ROOT / "data" / "intl" / "nepal" / "full.jsonl.gz"],
     "note": "Tender notices only: this publication has no award or winner data."},
    {"id": "in_as", "country": "India (Assam state)", "country_bn": "ভারত (আসাম রাজ্য)",
     "source": "Assam State Government Finance Department", "url": REGISTRY + "131",
     "files": [ROOT / "data" / "intl" / "india_assam" / "full.jsonl.gz"],
     "note": "Tender notices only: this publication has no award or winner data."},
]

CODELIST = {"open", "selective", "limited", "direct"}
MIN_AWARDS, DOMINANT = 30, 0.40
SHORT_DAYS = 7


def releases(paths):
    for p in paths:
        if not p.exists():
            continue
        op = gzip.open if p.suffix == ".gz" else open
        with op(p, "rt", encoding="utf8") as f:
            if ".jsonl" in p.name:
                for line in f:
                    if line.strip():
                        yield json.loads(line)
            else:
                yield from json.load(f)["releases"]


def buyer_name(r):
    name = (r.get("buyer") or {}).get("name") or ((r.get("tender") or {}).get("procuringEntity") or {}).get("name")
    if not name:
        for p in r.get("parties") or []:
            if {"buyer", "procuringEntity"} & set(p.get("roles") or []):
                name = p.get("name")
                break
    return " ".join(str(name or "").split())


def _date(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def check(ds):
    seen = set()
    n_rel = n_tenders = 0
    first = last = None
    methods = Counter()
    bids = Counter()
    windows, bad_windows = [], 0
    by_buyer = defaultdict(Counter)
    value = defaultdict(Counter)            # currency -> supplier -> amount
    n_awards = 0
    names = {}
    for r in releases(ds["files"]):
        n_rel += 1
        d = _date(r.get("date"))
        if d:
            d = d.replace(tzinfo=None)
            first, last = min(first or d, d), max(last or d, d)
        t = r.get("tender") or {}
        ocid = r.get("ocid")
        if ocid not in seen:                 # tender-level facts once per contracting process
            seen.add(ocid)
            n_tenders += 1
            m = t.get("procurementMethod")
            methods[m if m in CODELIST else ("missing" if not m else "not in codelist")] += 1
            k = t.get("numberOfTenderers")
            if isinstance(k, (int, float)) and k >= 1:
                bids["one" if k == 1 else "more"] += 1
            tp = t.get("tenderPeriod") or {}
            s, e = _date(tp.get("startDate")), _date(tp.get("endDate"))
            if m == "open" and s and e:
                if e.date() <= s.date():         # ends on or before the day it starts: a placeholder or error
                    bad_windows += 1
                else:
                    windows.append((e - s).total_seconds() / 86400)
        buyer = buyer_name(r)
        for a in r.get("awards") or []:
            if a.get("status") in ("cancelled", "unsuccessful"):
                continue
            sups = [s for s in a.get("suppliers") or [] if s.get("name") or s.get("id")]
            if not sups:
                continue
            n_awards += 1
            v = a.get("value") or {}
            for s in sups:
                key = " ".join(str(s.get("name") or s.get("id")).lower().split())
                names.setdefault(key, " ".join(str(s.get("name") or s.get("id")).split()))
                if buyer:
                    by_buyer[buyer][key] += 1
                if isinstance(v.get("amount"), (int, float)) and v.get("currency") and v["amount"] > 0:
                    value[v["currency"]][key] += v["amount"] / len(sups)

    out = {k: ds.get(k) for k in ("id", "country", "country_bn", "source", "url", "note")}
    out.update({"releases": n_rel, "tenders": n_tenders, "awards_with_supplier": n_awards,
                "buyers": len({b for b in by_buyer}) or None,
                "period": [first.date().isoformat(), last.date().isoformat()] if first else None})
    checks = {}

    eligible = {b: c for b, c in by_buyer.items() if sum(c.values()) >= MIN_AWARDS}
    if eligible:
        rows = []
        for b, c in eligible.items():
            sup, n = c.most_common(1)[0]
            tot = sum(c.values())
            rows.append({"buyer": b, "supplier": names[sup], "share": round(n / tot, 3), "won": n, "awards": tot})
        flagged = [x for x in rows if x["share"] >= DOMINANT]
        checks["dominance"] = {"available": True, "buyers_checked": len(rows), "flagged": len(flagged),
                               "share": round(len(flagged) / len(rows), 4),
                               "examples": sorted(flagged, key=lambda x: (-x["share"], -x["awards"]))[:8]}
    else:
        checks["dominance"] = {"available": False, "why": "no award winners in this data"}

    std = sum(v for k, v in methods.items() if k in CODELIST)
    checks["direct"] = ({"available": True, "tenders_with_method": std, "direct": methods["direct"],
                         "share": round(methods["direct"] / std, 4), "methods": dict(methods)}
                        if std else {"available": False, "why": "buying method not given in the OCDS codelist",
                                     "methods": dict(methods)})
    nb = bids["one"] + bids["more"]
    checks["single_bid"] = ({"available": True, "tenders_with_count": nb, "single": bids["one"],
                             "share": round(bids["one"] / nb, 4)} if nb else
                            {"available": False, "why": "number of tenders received not given"})
    with_dates = len(windows) + bad_windows
    if with_dates and bad_windows / with_dates > 0.2:
        checks["short_window"] = {"available": False, "data_quality": True,
                                  "why": f"bidding window dates look unreliable: {bad_windows / with_dates:.0%} of open "
                                         "tenders end on or before the day they start",
                                  "unreliable_share": round(bad_windows / with_dates, 4)}
    else:
        checks["short_window"] = ({"available": True, "open_tenders_with_dates": len(windows),
                               "short": sum(1 for w in windows if w < SHORT_DAYS),
                               "share": round(sum(1 for w in windows if w < SHORT_DAYS) / len(windows), 4),
                                   "median_days": round(sorted(windows)[len(windows) // 2], 1)} if windows else
                                  {"available": False, "why": "bidding window start and end dates not given"})
    if value:
        cur, sups = max(value.items(), key=lambda kv: sum(kv[1].values()))
        amounts = sorted(sups.values(), reverse=True)
        top = max(1, math.ceil(len(amounts) * 0.05))
        checks["concentration"] = {"available": True, "currency": cur, "suppliers": len(amounts),
                                   "top5pct_suppliers": top,
                                   "top5pct_share_of_value": round(sum(amounts[:top]) / sum(amounts), 4)}
    else:
        checks["concentration"] = {"available": False, "why": "no award values with a winner"}
    out["checks"] = checks
    return out


def main():
    results = []
    for ds in DATASETS:
        r = check(ds)
        results.append(r)
        print(ds["id"], r["releases"], "releases;",
              {k: (v.get("share") if v["available"] else "n/a") for k, v in r["checks"].items()}, flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"made": datetime.now().strftime("%Y-%m-%d"),
                               "thresholds": {"dominance_min_awards": MIN_AWARDS, "dominance_share": DOMINANT,
                                              "short_window_days": SHORT_DAYS, "concentration_top": "5% of suppliers"},
                               "datasets": results}, ensure_ascii=False, indent=1), encoding="utf8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
