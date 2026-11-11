"""Export all Bangladesh e-GP awards as OCDS 1.1 release packages, one gzip file per year, and validate them.

    python pipeline/export_ocds.py              # export + validate a random sample
    python pipeline/export_ocds.py --validate   # only validate the existing files
    python pipeline/export_ocds.py --no-validate   # only export (weekly, on the server)

Output: data/ocds/bd-egp-<year>.json.gz (release packages) and data/ocds/manifest.json.
Validation uses the official OCDS 1.1.5 release-package schema (downloaded once to data/ocds/schema/).
"""
import gzip
import json
import random
import sys
import urllib.request
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.ocds import package, release  # noqa: E402

DB = ROOT / "data" / "prohori.duckdb"
OUT = ROOT / "data" / "ocds"
DETAIL = ROOT / "data" / "detail_contracts.parquet"
SCHEMA_BASE = "https://standard.open-contracting.org/schema/1__1__5/"
COLS = ("tender_id, pkg_lot_id, title, ministry, procuring_entity, method, district, signed_date, advertised_at, "
        "winner, winner_key, is_jv, value_bdt, foreign_currency, foreign_amount, fetched_at")


def export():
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB), read_only=True)
    received = {}
    if DETAIL.exists():
        received = {(str(t), str(p)): r for t, p, r in con.execute(
            f"SELECT tender_id, pkg_lot_id, received FROM read_parquet('{DETAIL.as_posix()}') "
            "WHERE received IS NOT NULL").fetchall()}
    years = [y for (y,) in con.execute("SELECT DISTINCT year(signed_date) FROM contracts ORDER BY 1").fetchall()]
    manifest = []
    for y in years:
        cur = con.execute(f"SELECT {COLS} FROM contracts WHERE year(signed_date) = ? ORDER BY signed_date, tender_id", [y])
        cols = [d[0] for d in cur.description]
        name = f"bd-egp-{y}.json.gz"
        head = json.dumps(package([], f"https://prohori.safeshare.co/ocds/{name}"), ensure_ascii=False)
        n = n_bids = 0
        # Written one release at a time, so a small server can export big years without running out of memory.
        with gzip.open(OUT / name, "wt", encoding="utf8") as f:
            f.write(head[:-len("[]}")] + "[")
            while rows := cur.fetchmany(5000):
                for row in rows:
                    r = dict(zip(cols, row))
                    rel = release(r, received.get((str(r["tender_id"]), str(r["pkg_lot_id"]))))
                    f.write(("," if n else "") + json.dumps(rel, ensure_ascii=False, default=str))
                    n += 1
                    n_bids += "numberOfTenderers" in rel["tender"]
            f.write("]}")
        manifest.append({"year": y, "file": name, "releases": n, "with_tenderers": n_bids,
                         "bytes": (OUT / name).stat().st_size})
        print(y, n, "releases", flush=True)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf8")


def _schema():
    d = OUT / "schema"
    d.mkdir(parents=True, exist_ok=True)
    for n in ("release-package-schema.json", "release-schema.json"):
        if not (d / n).exists():
            (d / n).write_bytes(urllib.request.urlopen(SCHEMA_BASE + n, timeout=60).read())
    return json.loads((d / "release-package-schema.json").read_text(encoding="utf8")), \
        json.loads((d / "release-schema.json").read_text(encoding="utf8"))


def validate(sample_per_year=300):
    """Validate the package wrapper and a random sample of releases from every year against the official schema."""
    from jsonschema import Draft4Validator
    pkg_schema, rel_schema = _schema()
    rel_v = Draft4Validator(rel_schema)
    pkg_schema = json.loads(json.dumps(pkg_schema))
    pkg_schema["properties"]["releases"] = {"type": "array"}       # releases are checked one by one below
    pkg_v = Draft4Validator(pkg_schema)
    random.seed(7)
    report = {"schema": SCHEMA_BASE + "release-package-schema.json", "files": 0, "releases_checked": 0, "errors": []}
    for f in sorted(OUT.glob("bd-egp-*.json.gz")):
        with gzip.open(f, "rt", encoding="utf8") as fh:
            pkg = json.load(fh)
        report["files"] += 1
        report["errors"] += [f"{f.name}: {e.message}" for e in pkg_v.iter_errors(pkg)][:5]
        rels = pkg["releases"]
        for r in random.sample(rels, min(sample_per_year, len(rels))):
            report["releases_checked"] += 1
            errs = [f"{f.name} {r['id']}: {'/'.join(map(str, e.path))} {e.message}" for e in rel_v.iter_errors(r)]
            report["errors"] += errs[:3]
    report["valid"] = not report["errors"]
    (OUT / "validation.json").write_text(json.dumps(report, indent=1), encoding="utf8")
    print(json.dumps({k: v for k, v in report.items() if k != "errors"}), "errors:", len(report["errors"]))
    for e in report["errors"][:10]:
        print("  ", e)
    return report


if __name__ == "__main__":
    if "--validate" not in sys.argv:
        export()
    if "--no-validate" not in sys.argv:     # the weekly server run skips it (validation loads whole years in memory)
        validate()
