"""Build the Prohori database (data/prohori.duckdb) from the raw collected files.

Re-runnable: drops and rebuilds the tables each time, so run it again whenever more
raw data has been collected.

Tables:
  contracts   one row per awarded contract (deduplicated across collectors)
  debarments  one row per debarment record
"""
import glob
import json
import re
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

from names import clean_name, is_joint_venture, strict_key

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "prohori.duckdb"

CRORE = 10_000_000


def parse_value(raw: str):
    """Return (value_bdt, foreign_currency, foreign_amount).

    Plain numbers are crore taka ("4.550"). Tagged values look like
    "BDT: 724500.000 EUR: 889827.040" and are in full units.
    """
    raw = raw.strip()
    if re.fullmatch(r"[\d.]+", raw):
        return float(raw) * CRORE, None, None
    parts = dict((cur, float(amt)) for cur, amt in re.findall(r"([A-Z]{3}):\s*([\d.]+)", raw))
    bdt = parts.pop("BDT", None)
    foreign = next(iter(parts.items()), (None, None))
    return bdt, foreign[0], foreign[1]


def parse_date(raw: str, fmt: str):
    try:
        return datetime.strptime(raw.strip(), fmt)
    except (ValueError, AttributeError):
        return None


def load_contracts() -> pd.DataFrame:
    rows = []
    for f in sorted(glob.glob(str(RAW / "noa" / "noa*.jsonl"))):
        with open(f, encoding="utf8") as fh:
            for line in fh:
                rows.append(json.loads(line))
    df = pd.DataFrame(rows)
    raw_count = len(df)

    # Same contract can appear twice (collector overlaps, pages shifting). Keep the latest fetch.
    df["key"] = df["pkgLotId"].fillna("") + "|" + df["tenderId"].fillna("") + "|" + df["winner"]
    df = df.sort_values("fetchedAt").drop_duplicates("key", keep="last")

    parsed = df["value"].map(parse_value)
    df["value_bdt"] = parsed.map(lambda t: t[0])
    df["foreign_currency"] = parsed.map(lambda t: t[1])
    df["foreign_amount"] = parsed.map(lambda t: t[2])
    df["signed_date"] = df["contractSigned"].map(lambda s: parse_date(s, "%d-%b-%Y"))
    df["advertised_at"] = df["advertised"].map(lambda s: parse_date(s, "%d-%b-%Y %H:%M"))
    df["winner_clean"] = df["winner"].map(clean_name)
    df["winner_key"] = df["winner"].map(strict_key)
    df["is_jv"] = df["winner"].map(is_joint_venture)
    df["ref_no"] = df["idAndRef"].str.split(",", n=1).str[1].str.strip()

    out = df[[
        "tenderId", "pkgLotId", "ref_no", "title", "ministry", "procuringEntity", "method",
        "district", "signed_date", "advertised_at", "winner", "winner_clean", "winner_key",
        "is_jv", "value_bdt", "foreign_currency", "foreign_amount", "value", "fetchedAt",
    ]].rename(columns={
        "tenderId": "tender_id", "pkgLotId": "pkg_lot_id", "procuringEntity": "procuring_entity",
        "value": "value_raw", "fetchedAt": "fetched_at",
    })
    print(f"contracts: {raw_count:,} raw rows -> {len(out):,} unique")
    return out


def load_debarments() -> pd.DataFrame:
    rows = [json.loads(l) for l in open(RAW / "debarment" / "debarment.jsonl", encoding="utf8")]
    df = pd.DataFrame(rows)
    period = df["period"].str.extract(r"(\d{2}-\w{3}-\d{4})\s*to\s*(\d{2}-\w{3}-\d{4})")
    df["debar_from"] = period[0].map(lambda s: parse_date(s, "%d-%b-%Y"))
    df["debar_to"] = period[1].map(lambda s: parse_date(s, "%d-%b-%Y"))
    df["company_clean"] = df["company"].map(clean_name)
    df["company_key"] = df["company"].map(strict_key)
    out = df[["company", "company_clean", "company_key", "address", "area", "debar_from",
              "debar_to", "debarredBy", "reason"]].rename(columns={"debarredBy": "debarred_by"})
    print(f"debarments: {len(out):,} records, {out['company_key'].nunique():,} unique companies")
    return out


def main():
    contracts = load_contracts()
    debarments = load_debarments()
    con = duckdb.connect(str(DB_PATH))
    # Register under new names: a bare "FROM contracts" would read the existing table, not the DataFrame.
    con.register("contracts_df", contracts)
    con.register("debarments_df", debarments)
    con.execute("CREATE OR REPLACE TABLE contracts AS SELECT * FROM contracts_df")
    con.execute("CREATE OR REPLACE TABLE debarments AS SELECT * FROM debarments_df")

    s = con.execute("""
        SELECT count(*), sum(value_bdt) / 1e7, min(signed_date), max(signed_date),
               count(DISTINCT winner_key), count(DISTINCT procuring_entity)
        FROM contracts""").fetchone()
    print(f"\nunique contracts : {s[0]:,}")
    print(f"total value      : Tk {s[1]:,.0f} crore")
    print(f"date range       : {s[2]:%d %b %Y} -> {s[3]:%d %b %Y}")
    print(f"unique companies : {s[4]:,}")
    print(f"buying offices   : {s[5]:,}")
    print(f"database         : {DB_PATH}")
    con.close()


if __name__ == "__main__":
    main()
