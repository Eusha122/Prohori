"""Pick which contract detail pages to download (case-control sample).

- every entity (name + division) linked to a debarment: up to 10 contracts, most recent before its ban
- a random sample of other entities that appear in the training/test snapshots: up to 5 recent contracts

Writes data/raw/detail/targets.csv (tender_id, pkg_lot_id, entity, group).
"""
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

import train_model as tm

OUT = tm.ROOT / "data" / "raw" / "detail" / "targets.csv"
OUT_RANDOM = tm.ROOT / "data" / "raw" / "detail" / "targets_random_history.csv"   # used for modelling
OUT_B_FETCH = tm.ROOT / "data" / "raw" / "detail" / "targets_b.csv"               # pages still to fetch
N_NEGATIVE_ENTITIES = 5000
PER_POSITIVE, PER_NEGATIVE, PER_RANDOM = 10, 5, 6


def main():
    con = duckdb.connect(str(tm.DB_PATH), read_only=True)
    c = tm.load(con)
    c = c[c["pkg_lot_id"].notna()] if "pkg_lot_id" in c else c
    ids = con.execute("SELECT tender_id, pkg_lot_id, winner_key, signed_date, district FROM contracts "
                      "WHERE pkg_lot_id IS NOT NULL AND signed_date IS NOT NULL").df()
    ids = ids.merge(c[["winner_key", "signed_date", "district", "entity"]].drop_duplicates(),
                    on=["winner_key", "signed_date", "district"], how="left")
    first_ban = tm.debarment_events(con)

    pos_ent = set(first_ban.index) & set(ids["entity"].dropna())
    pos = ids[ids["entity"].isin(pos_ent)].copy()
    pos["ban"] = pos["entity"].map(first_ban)
    pos["before"] = pos["signed_date"] < pos["ban"]
    # Prefer contracts before the ban (what the model sees), most recent first.
    pos = (pos.sort_values(["entity", "before", "signed_date"], ascending=[True, False, False])
              .groupby("entity").head(PER_POSITIVE))
    pos["group"] = "debarred_link"

    active = ids[(ids["signed_date"] >= "2014-01-01") & ~ids["entity"].isin(pos_ent)]
    sample_ent = pd.Series(active["entity"].dropna().unique()).sample(N_NEGATIVE_ENTITIES, random_state=42)
    neg = (active[active["entity"].isin(set(sample_ent))].sort_values("signed_date", ascending=False)
           .groupby("entity").head(PER_NEGATIVE))
    neg["group"] = "random_sample"

    out = pd.concat([pos, neg])[["tender_id", "pkg_lot_id", "entity", "group"]].drop_duplicates(["tender_id", "pkg_lot_id"])
    out = out.sample(frac=1, random_state=1)   # shuffle so every worker gets a mix
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if not OUT.exists():
        out.to_csv(OUT, index=False)
    print(f"positive-linked entities: {len(pos_ent):,} -> {len(pos):,} contracts")
    print(f"random entities: {N_NEGATIVE_ENTITIES:,} -> {len(neg):,} contracts")
    print(f"batch A detail pages: {len(out):,} -> {OUT}")

    # Batch B: the SAME random draw of contracts across each sampled entity's whole history, for both
    # groups, so detail-based features are measured identically for debarred-linked and other firms.
    entities = set(pos_ent) | set(sample_ent)
    hist = ids[ids["entity"].isin(entities)]
    rnd = hist.sample(frac=1, random_state=7).groupby("entity").head(PER_RANDOM)
    rnd = rnd.assign(group=np.where(rnd["entity"].isin(pos_ent), "debarred_link", "random_sample"))
    rnd[["tender_id", "pkg_lot_id", "entity", "group"]].to_csv(OUT_RANDOM, index=False)
    new = rnd[~rnd["pkg_lot_id"].isin(set(out["pkg_lot_id"]))]
    new[["tender_id", "pkg_lot_id", "entity", "group"]].sample(frac=1, random_state=2).to_csv(OUT_B_FETCH, index=False)
    print(f"batch B (random history, {PER_RANDOM}/entity): {len(rnd):,} contracts, {len(new):,} not yet fetched -> {OUT_B_FETCH}")


if __name__ == "__main__":
    main()
