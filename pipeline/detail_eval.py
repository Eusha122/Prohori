"""Do contract detail pages (bidder counts, late signing, ...) improve the risk model?

Detail pages were downloaded for a sample of entities: every entity linked to a debarment plus a
random 5,000 others. For modelling we use ONLY the "random history" pages (the same random draw of
up to 6 contracts per entity across its whole history, for both groups), so debarred-linked and
other firms are measured the same way. Random-sample entities get a weight equal to
(eligible other entities / 5,000), so weighted metrics estimate the full population.

Compares, on the same entities and the same time split:
  base   = logistic regression on the existing features
  detail = logistic regression on the existing features + detail-page features
and reports a paired bootstrap (resampling entities) for the AUC difference.

Writes models/detail_eval.json and data/detail_contracts.parquet (one row per detail page).
"""
import glob
import json
import re

import duckdb
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import train_model as tm

DETAIL_DIR = tm.ROOT / "data" / "raw" / "detail"
OUT_PARQUET = tm.ROOT / "data" / "detail_contracts.parquet"

DETAIL_FEATURES = {
    "d_share_single_bid": "share of sampled contracts with only one tender received",
    "d_avg_received": "average number of tenders received",
    "d_share_one_responsive": "share where at most one tender was responsive",
    "d_share_low_uptake": "share where under half of sold tender documents were submitted",
    "d_share_ps_late": "share where performance security was not given in time",
    "d_share_sign_late": "share where the contract was not signed in time",
    "d_share_aid": "share funded by a development partner",
    "d_share_revenue": "share paid from the revenue budget",
    "d_addr_banned": "shares a business address with a different firm already banned",
}


def num(v):
    try:
        return float(str(v).strip())
    except ValueError:
        return np.nan


def norm_addr(a: str) -> str:
    a = re.sub(r"[^a-z0-9 ]", " ", str(a or "").lower())
    return re.sub(r"\s+", " ", a).strip()


def specific(a: str) -> bool:
    """Only long addresses with a number (house/holding/road) are specific enough to link firms."""
    return len(a) >= 20 and bool(re.search(r"\d", a))


def load_details() -> pd.DataFrame:
    rows = []
    for f in glob.glob(str(DETAIL_DIR / "detail_*w*.jsonl")):
        for line in open(f, encoding="utf8"):
            r = json.loads(line)
            x = r["fields"]
            sold = num(x.get("No. of Tenders/Proposals Sold", ""))
            rec = num(x.get("No. of Tenders/Proposals Received", ""))
            resp = num(x.get("Tenders/Proposals Responsive", ""))
            yn = lambda k: {"yes": 0.0, "no": 1.0}.get(str(x.get(k, "")).strip().lower(), np.nan)
            budget = x.get("Budget and Source of Funds", "")
            addr = x.get("Location of Supplier/Contractor/Consultant") or x.get("Business Address of the Economic Operator", "")
            rows.append({
                "tender_id": str(r["tender_id"]), "pkg_lot_id": str(r["pkg_lot_id"]),
                "signed": pd.to_datetime(x.get("Date of Contract Signing", ""), format="%d-%b-%Y", errors="coerce"),
                "sold": sold, "received": rec, "responsive": resp,
                "single_bid": float(rec == 1) if rec == rec else np.nan,
                "one_responsive": float(resp <= 1) if resp == resp else np.nan,
                "low_uptake": float(rec / sold < 0.5) if (rec == rec and sold == sold and sold > 0) else np.nan,
                "ps_late": yn("Was the Performance Security provided in due time?"),
                "sign_late": yn("Was the Contract Singed in due time?"),
                "aid": float(str(x.get("Development Partner (if applicable)", "NA")).strip() not in ("NA", "")),
                "revenue": float("Revenue" in budget),
                "address": norm_addr(addr),
                "n_owners": len(r.get("owners") or []),
            })
    d = pd.DataFrame(rows).drop_duplicates(["tender_id", "pkg_lot_id"])
    d.to_parquet(OUT_PARQUET)
    return d


def house_numbers(a: str) -> set:
    """Number tokens that identify a building (house/holding/shop/road), not 4-digit postcodes."""
    return {t for t in re.findall(r"\d+[a-z]?", a) if not re.fullmatch(r"\d{4}", t)}


def banned_addresses(con, det: pd.DataFrame) -> pd.DataFrame:
    """Link each detail-page address to debarred firms whose listed address is the same place.

    The debarment list appends area names to addresses, so we match fuzzily: one address's words
    must be (nearly) contained in the other's, they must share a house/holding/road number, and the
    shorter one must have at least 5 words. Returns (address, company_key, debar_from).
    """
    from rapidfuzz import fuzz, process
    deb = con.execute("SELECT company_key, address, debar_from FROM debarments").df()
    deb["addr"] = deb["address"].map(norm_addr)
    deb = deb[deb["addr"].map(specific)].reset_index(drop=True)
    ua = pd.Series(det.loc[det["address"].map(specific), "address"].unique())
    m = process.cdist(ua.tolist(), deb["addr"].tolist(), scorer=fuzz.token_set_ratio, score_cutoff=90, workers=-1)
    rows = []
    for i, j in zip(*np.nonzero(m)):
        a, b = ua.iat[i], deb["addr"].iat[j]
        if house_numbers(a) & house_numbers(b) and min(len(a.split()), len(b.split())) >= 5:
            rows.append((a, deb["company_key"].iat[j], deb["debar_from"].iat[j]))
    return pd.DataFrame(rows, columns=["address", "company_key", "debar_from"])


def load_all_addresses(det):
    return det[["address"]].drop_duplicates()


def detail_snapshot(det: pd.DataFrame, banned: pd.DataFrame, t: pd.Timestamp) -> pd.DataFrame:
    h = det[det["signed"] < t]
    g = h.groupby("entity")
    f = pd.DataFrame({
        "d_n": g.size(),
        "d_share_single_bid": g["single_bid"].mean(),
        "d_avg_received": g["received"].mean(),
        "d_share_one_responsive": g["one_responsive"].mean(),
        "d_share_low_uptake": g["low_uptake"].mean(),
        "d_share_ps_late": g["ps_late"].mean(),
        "d_share_sign_late": g["sign_late"].mean(),
        "d_share_aid": g["aid"].mean(),
        "d_share_revenue": g["revenue"].mean(),
    })
    # Address shared with a DIFFERENT firm that was banned before T.
    b = banned[banned["debar_from"] < t]
    hits = h.merge(b, on="address")
    hits = hits[hits["winner_key"] != hits["company_key"]]
    f["d_addr_banned"] = f.index.isin(set(hits["entity"])).astype(float)
    return f


def add_detail(snap: pd.DataFrame, det, banned) -> pd.DataFrame:
    parts = []
    for t, s in snap.groupby("T"):
        parts.append(s.join(detail_snapshot(det, banned, t), on="entity"))
    out = pd.concat(parts)
    out["d_n"] = out["d_n"].fillna(0)
    return out


def inputs(d, cols):
    x = tm.linear_inputs(d)
    for c in cols:
        if c.startswith("d_"):
            v = d[c].astype(float)
            x[c] = v.fillna(v.mean() if v.notna().any() else 0)
            if c == "d_avg_received":
                x[c] = np.log1p(x[c])
    # No "has detail pages" indicator: how many sampled pages fall before T depends on the firm's
    # FUTURE contract count (banned firms stop winning), so it would leak the label. Missing -> mean.
    return x


def fit(d, cols):
    m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000, C=0.5))
    w = d["w"] * np.where(d["label"] == 1, (d["w"] * (1 - d["label"])).sum() / (d["w"] * d["label"]).sum(), 1)
    m.fit(inputs(d, cols), d["label"], logisticregression__sample_weight=w)
    return m


def evaluate(train, test, seed=0):
    base_cols = list(tm.FEATURES)
    det_cols = base_cols + list(DETAIL_FEATURES)
    y, w = test["label"].to_numpy(), test["w"].to_numpy()
    mb, md = fit(train, base_cols), fit(train, det_cols)
    pb = mb.predict_proba(inputs(test, base_cols))[:, 1]
    pd_ = md.predict_proba(inputs(test, det_cols))[:, 1]

    def top10_recall(p):
        # weighted: flag the top 10% of the (weighted) population
        order = np.argsort(-p)
        cw = np.cumsum(w[order]) / w.sum()
        flagged = order[cw <= 0.10]
        return float(y[flagged].sum() / y.sum())

    rng = np.random.default_rng(seed)
    ents = test["entity"].unique()
    idx_by = test.groupby("entity").indices
    diffs, aucs_b, aucs_d = [], [], []
    for _ in range(300):
        idx = np.concatenate([idx_by[e] for e in rng.choice(ents, len(ents))])
        if 0 < y[idx].sum() < len(idx):
            a = roc_auc_score(y[idx], pb[idx], sample_weight=w[idx])
            b = roc_auc_score(y[idx], pd_[idx], sample_weight=w[idx])
            aucs_b.append(a); aucs_d.append(b); diffs.append(b - a)
    coefs = dict(zip(inputs(test, det_cols).columns, md[-1].coef_[0]))
    return {
        "test_rows": int(len(y)), "test_positives": int(y.sum()),
        "coverage_detail": float((test["d_n"] > 0).mean()),
        "base_auc": float(roc_auc_score(y, pb, sample_weight=w)),
        "detail_auc": float(roc_auc_score(y, pd_, sample_weight=w)),
        "auc_gain": float(np.mean(diffs)), "auc_gain_95ci": [float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))],
        "share_of_bootstraps_improved": float(np.mean(np.array(diffs) > 0)),
        "base_top10_recall": top10_recall(pb), "detail_top10_recall": top10_recall(pd_),
        "detail_weights": {DETAIL_FEATURES.get(k, k): round(float(v), 3) for k, v in coefs.items() if k.startswith("d_")},
    }


def main():
    con = duckdb.connect(str(tm.DB_PATH), read_only=True)
    c = tm.load(con)
    con.register("c", c)
    first_ban = tm.debarment_events(con)

    det = load_details()
    sample = pd.read_csv(DETAIL_DIR / "targets_random_history.csv", dtype=str)
    det = det.merge(sample[["tender_id", "pkg_lot_id", "entity", "group"]], on=["tender_id", "pkg_lot_id"])
    det = det.merge(c[["tender_id", "pkg_lot_id", "winner_key"]].astype({"tender_id": str, "pkg_lot_id": str})
                    .drop_duplicates(["tender_id", "pkg_lot_id"]), on=["tender_id", "pkg_lot_id"], how="left")
    print(f"random-history detail pages available: {len(det):,} of {len(sample):,}")
    print("  single-bid share %.1f%% | sign late %.2f%% | security late %.2f%%" % (
        100 * det["single_bid"].mean(), 100 * det["sign_late"].mean(), 100 * det["ps_late"].mean()))
    banned = banned_addresses(con, load_all_addresses(det))
    cross = det.merge(banned, on="address")
    cross = cross[cross["winner_key"] != cross["company_key"]]
    print(f"address links to a different banned firm: {cross['entity'].nunique()} sampled entities")

    groups = sample.drop_duplicates("entity").set_index("entity")["group"]
    pos_ent = set(groups[groups == "debarred_link"].index)
    eligible = c[(c["signed_date"] >= "2014-01-01") & ~c["entity"].isin(pos_ent)]["entity"].nunique()
    w_rand = eligible / (groups == "random_sample").sum()
    print(f"weight for each random-sample entity: {w_rand:.1f}")

    def build(ts):
        s = pd.concat([tm.snapshot(con, t, first_ban) for t in ts], ignore_index=True)
        s = s[s["entity"].isin(groups.index)].copy()
        s["w"] = np.where(s["entity"].isin(pos_ent), 1.0, w_rand)
        return add_detail(s, det, banned)

    results = {}
    for name, tr_t, te_t in (("main_test", tm.TRAIN_T + tm.VALID_T, tm.TEST_T),
                             ("stability_fold", tm.FOLD_B["train"] + tm.FOLD_B["valid"], tm.FOLD_B["test"])):
        tr, te = build(tr_t), build(te_t)
        r = evaluate(tr, te)
        results[name] = r
        print(f"[{name}] rows {r['test_rows']:,} pos {r['test_positives']} | detail coverage {r['coverage_detail']:.0%} | "
              f"AUC base {r['base_auc']:.3f} -> with detail {r['detail_auc']:.3f} | gain {r['auc_gain']:+.3f} "
              f"(95% {r['auc_gain_95ci'][0]:+.3f}..{r['auc_gain_95ci'][1]:+.3f}, better in {r['share_of_bootstraps_improved']:.0%}) | "
              f"top10% recall {r['base_top10_recall']:.1%} -> {r['detail_top10_recall']:.1%}")
        print("   detail weights:", r["detail_weights"])
    (tm.MODEL_DIR / "detail_eval.json").write_text(json.dumps(results, indent=2), encoding="utf8")
    con.close()


if __name__ == "__main__":
    main()
