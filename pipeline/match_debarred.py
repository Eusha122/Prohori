"""Match debarred companies to the contracts they won, and report the match rate.

Writes table debar_matches(company_strict, winner, match_level, tender_id, pkg_lot_id,
signed_date, value_bdt, debar_from, before_ban) to data/prohori.duckdb.

Match levels (strictest first):
  exact  - same name after light cleaning (case, punctuation, M/S, Ltd, Pvt)
  fuzzy  - near-identical spelling (similarity >= 95, same first word)
  jv     - the debarred firm appears as a partner inside a joint-venture winner name
"""
import re
from pathlib import Path

import duckdb
import pandas as pd
from rapidfuzz import fuzz, process

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "prohori.duckdb"


def main():
    con = duckdb.connect(str(DB_PATH))
    contracts = con.execute(
        "SELECT tender_id, pkg_lot_id, winner, winner_key AS k, is_jv, signed_date, value_bdt "
        "FROM contracts").df()
    debar = con.execute("SELECT company_key AS k, debar_from FROM debarments").df()
    # Earliest ban date per company: contracts before it are the "before the ban" history.
    first_ban = debar.groupby("k")["debar_from"].min()
    debar_keys = sorted(k for k in first_ban.index if len(k) >= 4)

    winners = contracts["k"].unique().tolist()
    winner_set = set(winners)
    by_first_word = {}
    for w in winners:
        by_first_word.setdefault(w.split(" ")[0], []).append(w)

    def same_initials(a: str, b: str) -> bool:
        """Short tokens (initials like 'b h' vs 'b l') must match exactly; typos are only
        tolerated inside longer words."""
        short_a = [t for t in a.split() if len(t) <= 2]
        short_b = [t for t in b.split() if len(t) <= 2]
        return short_a == short_b

    links = []  # (debar_key, winner_key, level)
    for dk in debar_keys:
        if dk in winner_set:
            links.append((dk, dk, "exact"))
        candidates = by_first_word.get(dk.split(" ")[0], [])
        for wk, score, _ in process.extract(dk, candidates, scorer=fuzz.ratio, limit=5):
            if wk != dk and score >= 95 and same_initials(dk, wk):
                links.append((dk, wk, "fuzzy"))

    # Joint ventures: the debarred name appears as a whole phrase inside a JV winner.
    jv_keys = contracts.loc[contracts["is_jv"], "k"].unique()
    for dk in debar_keys:
        if len(dk.split()) < 2:
            continue  # single-word names are too ambiguous inside JV strings
        pat = re.compile(rf"\b{re.escape(dk)}\b")
        for wk in jv_keys:
            if wk != dk and pat.search(wk):
                links.append((dk, wk, "jv"))

    link_df = pd.DataFrame(links, columns=["company_strict", "k", "match_level"]).drop_duplicates()
    matched = link_df.merge(contracts, on="k")
    matched["debar_from"] = matched["company_strict"].map(first_ban)
    matched["before_ban"] = matched["signed_date"] < matched["debar_from"]
    out = matched[["company_strict", "winner", "match_level", "tender_id", "pkg_lot_id",
                   "signed_date", "value_bdt", "debar_from", "before_ban"]]
    con.register("debar_matches_df", out)
    con.execute("CREATE OR REPLACE TABLE debar_matches AS SELECT * FROM debar_matches_df")

    total = len(debar_keys)
    any_match = out["company_strict"].nunique()
    before = out[out["before_ban"]]
    print(f"debarred companies (unique names)      : {total}")
    print(f"matched to at least one contract       : {any_match} ({any_match / total:.0%})")
    print(f"matched with contracts BEFORE the ban  : {before['company_strict'].nunique()} "
          f"({before['company_strict'].nunique() / total:.0%})")
    print(f"contracts before ban (training 'bad')  : {len(before):,}")
    print("by match level (companies):")
    print(out.groupby("match_level")["company_strict"].nunique().to_string())
    print("\nfuzzy examples:")
    print(link_df[link_df.match_level == "fuzzy"].head(8).to_string(index=False))
    con.close()


if __name__ == "__main__":
    main()
