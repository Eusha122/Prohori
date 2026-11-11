"""Train the Prohori high-risk-contractor model and backtest it against later debarments.

Unit of prediction: an *entity* = company name (strict key) + division, so that different
firms sharing a common name in different parts of the country are kept apart.

For each snapshot date T we describe every active entity using only contracts signed before T,
and label it 1 if the entity was debarred within the following 24 months. Training uses
snapshots whose label windows end before the test period starts, so test debarments are never
seen during training (time-split backtest).

Writes:
  models/risk_logit.joblib, models/risk_gbm.txt   final ensemble parts (all labelled snapshots)
  models/metrics.json      backtest metrics
  DB table entity_risk     current risk score + top reasons for every active entity
"""
import json
from datetime import date
from pathlib import Path

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from geo import district_from_address, division_of
from names import strict_key

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "prohori.duckdb"
MODEL_DIR = ROOT / "models"

HORIZON_DAYS = 730          # label window: debarred within 24 months of the snapshot
ACTIVE_DAYS = 1095          # entity must have won a contract within 3 years before the snapshot
QUARTERS = ("01", "04", "07", "10")
# Label windows: train ends <= 2022-07, validation <= 2023-07, test debarments start 2023-07.
TRAIN_T = [f"{y}-{m}-01" for y in range(2016, 2021) for m in QUARTERS if f"{y}-{m}" <= "2020-07"]
VALID_T = ["2021-01-01", "2021-04-01", "2021-07-01"]
TEST_T = ["2023-07-01", "2023-10-01", "2024-01-01", "2024-04-01", "2024-07-01"]
# Second, earlier fold for the stability check (windows: train <= 2020-07, test debarments 2020-07..2023-07).
FOLD_B = {"train": [f"{y}-{m}-01" for y in range(2016, 2019) for m in QUARTERS if f"{y}-{m}" <= "2018-07"],
          "valid": ["2019-01-01", "2019-04-01"],
          "test": ["2020-07-01", "2020-10-01", "2021-01-01", "2021-04-01", "2021-07-01"]}
TODAY = date.today().isoformat()
CACHE_DIR = ROOT / "data" / "model_cache"

# Type of work, from contract titles (a contract can match several).
WORK_TYPES = {
    "road": r"\broad|\brcc\b|hbb|bitumen|carpet|pavement|highway|herring|bc road|gc road",
    "bridge": r"bridge|culvert",
    "building": r"building|storied|floor|school|office complex|hospital|mosque|shelter|dormitory|hall\b|tower",
    "repair": r"repair|maintenance|renovation|rehabilitat|periodic",
    "water": r"drain|water|tube ?well|sanitation|embankment|canal|khal|river|dredg|sluice|pond",
    "electric": r"electric|transformer|cable|solar|street ?light|substation|generator",
    "supply": r"supply|procurement of|purchase|furniture|equipment|medicine|vehicle|computer|printing|stationer",
    "service": r"cleaning|security service|consultan|outsourc|catering|survey|hiring|rental|service",
}

FEATURES = {
    "n_total": "contracts won (all time)",
    "n_12m": "contracts won in the last 12 months",
    "growth_12m": "growth in contracts vs the year before",
    "value_total": "total contract value",
    "value_12m": "contract value in the last 12 months",
    "avg_value": "average contract size",
    "max_value": "largest contract",
    "n_offices": "number of buying offices",
    "n_districts": "number of districts",
    "n_ministries": "number of ministries",
    "share_direct": "share of direct / single-source contracts",
    "share_ltm": "share of limited-tendering contracts",
    "share_rfq": "share of request-for-quotation contracts",
    "share_otm": "share of open-tendering contracts",
    "share_jv": "share won as a joint venture",
    "days_active": "time since first contract",
    "days_since_last": "time since last contract",
    "med_ad_to_sign": "typical days from advertisement to contract",
    "share_fast": "share of contracts signed under 21 days after advertisement",
    "top_office_share": "highest share of a single office's contracts",
    "n_dominated": "offices where it wins 40%+ of contracts",
    "top_office_concentration": "share of its own contracts from one office",
    "share_lged": "share of contracts from local-government engineering (LGED)",
    "share_roads": "share of contracts from roads & highways",
    "n_offices_12m": "buying offices in the last 12 months",
    "new_office_share_12m": "share of last year's offices that were new to it",
    "value_jump": "recent contract size vs its usual size",
    **{f"share_{k}": f"share of {k} contracts" for k in WORK_TYPES},
}

SNAPSHOT_SQL = """
WITH hist AS (SELECT * FROM c WHERE signed_date < DATE '{T}'),
office AS (SELECT procuring_entity, count(*) AS office_n FROM hist GROUP BY 1),
ew AS (SELECT entity, procuring_entity, count(*) AS n FROM hist GROUP BY 1, 2),
ent AS (
  SELECT entity,
    count(*) AS n_total,
    count(*) FILTER (WHERE signed_date >= DATE '{T}' - INTERVAL 365 DAY) AS n_12m,
    count(*) FILTER (WHERE signed_date >= DATE '{T}' - INTERVAL 730 DAY
                       AND signed_date <  DATE '{T}' - INTERVAL 365 DAY) AS n_prev12m,
    sum(value_bdt) AS value_total,
    coalesce(sum(value_bdt) FILTER (WHERE signed_date >= DATE '{T}' - INTERVAL 365 DAY), 0) AS value_12m,
    avg(value_bdt) AS avg_value,
    max(value_bdt) AS max_value,
    count(DISTINCT procuring_entity) AS n_offices,
    count(DISTINCT district) AS n_districts,
    count(DISTINCT ministry) AS n_ministries,
    avg(CASE WHEN method IN ('DPM', 'SSS') THEN 1 ELSE 0 END) AS share_direct,
    avg(CASE WHEN method = 'LTM' THEN 1 ELSE 0 END) AS share_ltm,
    avg(CASE WHEN method LIKE 'RFQ%' THEN 1 ELSE 0 END) AS share_rfq,
    avg(CASE WHEN method = 'OTM' THEN 1 ELSE 0 END) AS share_otm,
    avg(CASE WHEN is_jv THEN 1 ELSE 0 END) AS share_jv,
    date_diff('day', min(signed_date), DATE '{T}') AS days_active,
    date_diff('day', max(signed_date), DATE '{T}') AS days_since_last,
    median(date_diff('day', advertised_at, signed_date)) AS med_ad_to_sign,
    avg(CASE WHEN date_diff('day', advertised_at, signed_date) < 21 THEN 1 ELSE 0 END) AS share_fast,
    avg(CASE WHEN ministry ILIKE '%Local Government%' THEN 1 ELSE 0 END) AS share_lged,
    avg(CASE WHEN ministry ILIKE '%Road Transport%' THEN 1 ELSE 0 END) AS share_roads,
    count(DISTINCT procuring_entity) FILTER (WHERE signed_date >= DATE '{T}' - INTERVAL 365 DAY) AS n_offices_12m,
    avg(value_bdt) FILTER (WHERE signed_date >= DATE '{T}' - INTERVAL 365 DAY) AS avg_value_12m,
    {work_type_columns}
  FROM hist GROUP BY 1),
first_seen AS (SELECT entity, procuring_entity, min(signed_date) AS first_at FROM hist GROUP BY 1, 2),
newoff AS (
  SELECT entity,
    avg(CASE WHEN first_at >= DATE '{T}' - INTERVAL 365 DAY THEN 1 ELSE 0 END) AS new_office_share_12m
  FROM first_seen
  WHERE (entity, procuring_entity) IN (SELECT entity, procuring_entity FROM hist
                                       WHERE signed_date >= DATE '{T}' - INTERVAL 365 DAY)
  GROUP BY 1),
off AS (
  SELECT ew.entity,
    max(ew.n::DOUBLE / o.office_n) FILTER (WHERE o.office_n >= 20) AS top_office_share,
    count(*) FILTER (WHERE o.office_n >= 20 AND ew.n::DOUBLE / o.office_n >= 0.4) AS n_dominated,
    max(ew.n) AS top_office_n
  FROM ew JOIN office o USING (procuring_entity) GROUP BY 1)
SELECT ent.*, coalesce(off.top_office_share, 0) AS top_office_share,
       coalesce(off.n_dominated, 0) AS n_dominated,
       off.top_office_n::DOUBLE / ent.n_total AS top_office_concentration,
       (ent.n_12m + 1.0) / (ent.n_prev12m + 1.0) AS growth_12m,
       coalesce(newoff.new_office_share_12m, 0) AS new_office_share_12m,
       ent.avg_value_12m / nullif(ent.avg_value, 0) AS value_jump
FROM ent LEFT JOIN off USING (entity) LEFT JOIN newoff USING (entity)
WHERE ent.days_since_last <= {active}
"""


def load(con) -> pd.DataFrame:
    df = con.execute("""
        SELECT tender_id, pkg_lot_id, winner_key, winner_clean, signed_date, advertised_at, value_bdt,
               method, procuring_entity, district, ministry, is_jv, title
        FROM contracts WHERE signed_date IS NOT NULL""").df()
    div = {d: division_of(d) for d in df["district"].dropna().unique()}
    df["division"] = df["district"].map(div).fillna("Unknown")
    df["entity"] = df["winner_key"] + "|" + df["division"]
    title = df["title"].fillna("").str.lower()
    for k, pattern in WORK_TYPES.items():
        df[f"wt_{k}"] = title.str.contains(pattern, regex=True).astype("int8")
    return df


def snapshot_sql(t: str) -> str:
    cols = ",\n    ".join(f"avg(wt_{k}) AS share_{k}" for k in WORK_TYPES)
    return SNAPSHOT_SQL.format(T=t, active=ACTIVE_DAYS, work_type_columns=cols)


def debarment_events(con) -> pd.Series:
    """First debarment date per entity (name + division of the debarred firm's address)."""
    deb = con.execute("SELECT company_key, address, debar_from FROM debarments").df()
    links = con.execute("SELECT DISTINCT company_strict, winner FROM debar_matches "
                        "WHERE match_level IN ('exact', 'fuzzy')").df()
    links["wk"] = links["winner"].map(strict_key)
    name_map = links.groupby("company_strict")["wk"].apply(set).to_dict()
    rows = []
    for r in deb.itertuples():
        division = division_of(district_from_address(r.address))
        for wk in name_map.get(r.company_key, {r.company_key}):
            rows.append((f"{wk}|{division}", r.debar_from))
    ev = pd.DataFrame(rows, columns=["entity", "debar_from"])
    return ev.groupby("entity")["debar_from"].min()


def snapshot(con, t: str, first_ban: pd.Series, cache: bool = True) -> pd.DataFrame:
    import hashlib
    version = hashlib.md5((snapshot_sql("X") + str(sorted(WORK_TYPES.items()))).encode()).hexdigest()[:8]
    path = CACHE_DIR / f"snap_{version}_{t}.parquet"
    if cache and path.exists():
        snap = pd.read_parquet(path)
    else:
        snap = con.execute(snapshot_sql(t)).df()
        if cache:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            snap.to_parquet(path)
    snap["T"] = pd.Timestamp(t)
    fb = snap["entity"].map(first_ban)
    snap = snap[~(fb < snap["T"])].copy()          # already debarred before T: not a prediction
    fb = snap["entity"].map(first_ban)
    snap["label"] = ((fb >= snap["T"]) & (fb < snap["T"] + pd.Timedelta(days=HORIZON_DAYS))).astype(int)
    snap["days_to_ban"] = (fb - snap["T"]).dt.days
    return snap




HEAVY_TAILED = ["n_total", "n_12m", "value_total", "value_12m", "avg_value", "max_value", "n_offices",
                "n_districts", "n_ministries", "days_active", "days_since_last", "med_ad_to_sign",
                "n_dominated", "n_offices_12m", "growth_12m", "value_jump"]
SIZE = ["n_total", "value_total", "n_12m"]


def linear_inputs(d: pd.DataFrame) -> pd.DataFrame:
    x = d[list(FEATURES)].astype(float).fillna(0).clip(lower=0)
    for col in HEAVY_TAILED:
        x[col] = np.log1p(x[col])
    return x


def fit_logit(d):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced", C=0.5)
                         ).fit(linear_inputs(d), d["label"])


GBM_PARAMS = dict(objective="binary", metric="auc", num_leaves=7, min_child_samples=300, learning_rate=0.02,
                  feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=5.0, verbose=-1, seed=42,
                  monotone_constraints=[1 if f in SIZE else 0 for f in FEATURES])


def ensemble_score(logit, gbm, d, rounds=None):
    """Average of the two models' percentile ranks within the given population (0..1, higher = riskier)."""
    from scipy.stats import rankdata
    a = rankdata(logit.predict_proba(linear_inputs(d))[:, 1])
    b = rankdata(gbm.predict(d[list(FEATURES)], num_iteration=rounds))
    return (a + b) / (2 * len(d))


def top_k_stats(y, p, frac):
    k = max(1, int(len(p) * frac))
    hits = y[np.argsort(-p)[:k]].sum()
    return {"precision": float(hits / k), "recall": float(hits / max(1, y.sum())),
            "lift": float((hits / k) / max(1e-9, y.mean()))}


def backtest(train, valid, test, seed=0):
    """Fit both parts on `train` (validation picks tree count) and measure on `test`."""
    X = list(FEATURES)
    logit = fit_logit(train)
    gbm = lgb.train(GBM_PARAMS, lgb.Dataset(train[X], train["label"]), 4000,
                    valid_sets=[lgb.Dataset(valid[X], valid["label"])],
                    callbacks=[lgb.early_stopping(300, verbose=False)])
    y = test["label"].to_numpy()
    p = ensemble_score(logit, gbm, test, gbm.best_iteration)

    size_cols = lambda d: np.log1p(d[SIZE].fillna(0).clip(lower=0))
    from sklearn.linear_model import LogisticRegression
    size_model = LogisticRegression(max_iter=1000, class_weight="balanced").fit(size_cols(train), train["label"])
    p_size = size_model.predict_proba(size_cols(test))[:, 1]

    bins = pd.qcut(test["n_total"].rank(method="first"), 10, labels=False).to_numpy()
    def within(pred):
        return float(np.mean([roc_auc_score(y[bins == b], pred[bins == b]) for b in range(10)
                              if 0 < y[bins == b].sum() < (bins == b).sum()]))

    t2 = test.assign(p=p)
    t2["pct_rank"] = t2.groupby("T")["p"].rank(pct=True, ascending=False)
    pos = t2[t2["label"] == 1]
    lead = pos[pos["pct_rank"] <= 0.10].groupby("entity")["days_to_ban"].max()

    # Confidence range: resample entities (not rows) with replacement.
    rng = np.random.default_rng(seed)
    ents = test["entity"].unique()
    idx_by_ent = test.groupby("entity").indices
    boot = []
    for _ in range(200):
        pick = rng.choice(ents, size=len(ents), replace=True)
        idx = np.concatenate([idx_by_ent[e] for e in pick])
        if 0 < y[idx].sum() < len(idx):
            boot.append(roc_auc_score(y[idx], p[idx]))

    return {
        "test_rows": int(len(y)), "test_positives": int(y.sum()), "base_rate": float(y.mean()),
        "roc_auc": float(roc_auc_score(y, p)),
        "roc_auc_95ci": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
        "pr_auc": float(average_precision_score(y, p)),
        "top_1pct": top_k_stats(y, p, 0.01), "top_5pct": top_k_stats(y, p, 0.05),
        "top_10pct": top_k_stats(y, p, 0.10),
        "auc_within_size_deciles": within(p),
        "auc_per_snapshot": {str(t.date()): float(roc_auc_score(g["label"], g["p"]))
                             for t, g in t2.groupby("T") if 0 < g["label"].sum() < len(g)},
        "size_only_baseline": {"roc_auc": float(roc_auc_score(y, p_size)),
                               "top_5pct": top_k_stats(y, p_size, 0.05), "auc_within_size_deciles": within(p_size)},
        "caught_in_advance": {
            "banned_entities_in_test": int(pos["entity"].nunique()),
            "flagged_top10pct_before_ban": int(lead.size),
            "share": float(lead.size / max(1, pos["entity"].nunique())),
            "median_months_before_ban": float(lead.median() / 30.4) if lead.size else None,
        },
        "gbm_rounds": int(gbm.best_iteration),
        "_models": (logit, gbm),
    }


def write_scores(con, c, first_ban, logit_f, gbm_f) -> pd.DataFrame:
    """Score every active entity as of today with the given models and save table entity_risk."""
    X = list(FEATURES)
    now = snapshot(con, date.today().isoformat(), first_ban, cache=False)
    now["risk_pct"] = ensemble_score(logit_f, gbm_f, now)
    z = logit_f[0].transform(linear_inputs(now))
    contrib = z * logit_f[-1].coef_[0]
    now["reasons"] = [json.dumps([{"signal": FEATURES[X[i]], "push": round(float(row[i]), 2)}
                                  for i in np.argsort(-row)[:3] if row[i] > 0.2]) for row in contrib]
    names = c.groupby("entity")["winner_clean"].agg(lambda s: s.mode().iat[0])
    now["name"] = now["entity"].map(names)
    now[["winner_key", "division"]] = now["entity"].str.rsplit("|", n=1, expand=True)
    out = now[["entity", "winner_key", "division", "name", "risk_pct", "reasons"] + X]
    con.register("risk_df", out)
    con.execute("CREATE OR REPLACE TABLE entity_risk AS SELECT * FROM risk_df")
    return out


def score_only():
    """Weekly refresh: re-score all active entities with the SAVED models (no retraining, same tested model)."""
    import joblib
    con = duckdb.connect(str(DB_PATH))
    c = load(con)
    con.register("c", c)
    first_ban = debarment_events(con)
    logit_f = joblib.load(MODEL_DIR / "risk_logit.joblib")
    gbm_f = lgb.Booster(model_file=str(MODEL_DIR / "risk_gbm.txt"))
    out = write_scores(con, c, first_ban, logit_f, gbm_f)
    print(f"re-scored {len(out):,} active entities as of {date.today()}")
    con.close()


def main():
    import joblib

    MODEL_DIR.mkdir(exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    c = load(con)
    con.register("c", c)
    first_ban = debarment_events(con)
    print(f"entities: {c['entity'].nunique():,} | entities with a debarment: {len(first_ban):,}")

    def build(ts):
        return pd.concat([snapshot(con, t, first_ban) for t in ts], ignore_index=True)

    train, valid, test = build(TRAIN_T), build(VALID_T), build(TEST_T)
    for name, d in (("train", train), ("valid", valid), ("test", test)):
        print(f"{name}: {len(d):,} rows, {d['label'].sum():,} positives ({d['label'].mean():.3%})")
    X = list(FEATURES)

    main_fold = backtest(train, valid, test)
    logit, gbm = main_fold.pop("_models")
    fold_b = backtest(build(FOLD_B["train"]), build(FOLD_B["valid"]), build(FOLD_B["test"]))
    fold_b.pop("_models")

    metrics = {
        "model": "ensemble of logistic regression + monotone gradient boosting (rank average)",
        "horizon_months": HORIZON_DAYS // 30,
        "main_test": {"train": TRAIN_T, "valid": VALID_T, "test": TEST_T, **main_fold},
        "stability_fold": {"train": FOLD_B["train"], "valid": FOLD_B["valid"], "test": FOLD_B["test"], **fold_b},
        "logistic_weights": {FEATURES[f]: round(float(w), 3) for f, w in
                             sorted(zip(X, logit[-1].coef_[0]), key=lambda t: -abs(t[1]))},
    }

    # Final models on every labelled snapshot, then score all active entities today.
    full = pd.concat([train, valid, test], ignore_index=True)
    logit_f = fit_logit(full)
    gbm_f = lgb.train({k: v for k, v in GBM_PARAMS.items() if k != "metric"},
                      lgb.Dataset(full[X], full["label"]), max(50, main_fold["gbm_rounds"]))
    joblib.dump(logit_f, MODEL_DIR / "risk_logit.joblib")
    gbm_f.save_model(str(MODEL_DIR / "risk_gbm.txt"))

    out = write_scores(con, c, first_ban, logit_f, gbm_f)

    (MODEL_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2, default=str), encoding="utf8")
    for fold in ("main_test", "stability_fold"):
        m = metrics[fold]
        print(f"[{fold}] AUC {m['roc_auc']:.3f} (95% {m['roc_auc_95ci'][0]:.3f}-{m['roc_auc_95ci'][1]:.3f}) | "
              f"within-size {m['auc_within_size_deciles']:.3f} | top10% recall {m['top_10pct']['recall']:.1%} | "
              f"caught early {m['caught_in_advance']['share']:.1%} (~{m['caught_in_advance']['median_months_before_ban']:.0f} mo) | "
              f"size-only AUC {m['size_only_baseline']['roc_auc']:.3f}")
        print("   per snapshot:", {k: round(v, 3) for k, v in m["auc_per_snapshot"].items()})
    print(f"scored {len(out):,} active entities as of {TODAY}")
    con.close()


if __name__ == "__main__":
    import sys
    score_only() if "--score-only" in sys.argv else main()
