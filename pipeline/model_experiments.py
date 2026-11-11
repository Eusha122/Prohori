"""Compare model types on the same time-split snapshots (cached), to pick one that generalises.

Selection uses the validation snapshots only; the test numbers are reported, never tuned on.
"""
import json
from pathlib import Path

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import train_model as tm

CACHE = tm.ROOT / "data" / "model_cache"


def datasets():
    CACHE.mkdir(exist_ok=True)
    files = {k: CACHE / f"{k}.parquet" for k in ("train", "valid", "test")}
    if all(f.exists() for f in files.values()):
        return {k: pd.read_parquet(f) for k, f in files.items()}
    con = duckdb.connect(str(tm.DB_PATH), read_only=True)
    con.register("c", tm.load(con))
    first_ban = tm.debarment_events(con)
    out = {"train": tm.TRAIN_T, "valid": tm.VALID_T, "test": tm.TEST_T}
    out = {k: pd.concat([tm.snapshot(con, t, first_ban) for t in ts], ignore_index=True) for k, ts in out.items()}
    for k, d in out.items():
        d.to_parquet(files[k])
    return out


def prep_linear(d, cols):
    x = d[cols].astype(float).fillna(0).clip(lower=0)
    heavy = ["n_total", "n_12m", "value_total", "value_12m", "avg_value", "max_value", "n_offices",
             "n_districts", "n_ministries", "days_active", "days_since_last", "med_ad_to_sign", "n_dominated",
             "n_offices_12m", "growth_12m", "value_jump"]
    for c in heavy:
        if c in x:
            x[c] = np.log1p(x[c])
    return x


def evaluate(name, y_valid, p_valid, y_test, p_test, test):
    k = max(1, int(len(p_test) * 0.05))
    top = np.argsort(-p_test)[:k]
    bins = pd.qcut(test["n_total"].rank(method="first"), 10, labels=False).to_numpy()
    within = [roc_auc_score(y_test[bins == b], p_test[bins == b]) for b in range(10)
              if 0 < y_test[bins == b].sum() < (bins == b).sum()]
    return {"model": name, "valid_auc": round(roc_auc_score(y_valid, p_valid), 4),
            "test_auc": round(roc_auc_score(y_test, p_test), 4),
            "test_recall_top5": round(y_test[top].sum() / y_test.sum(), 4),
            "test_lift_top5": round((y_test[top].mean()) / y_test.mean(), 2),
            "within_size_auc": round(float(np.mean(within)), 4)}


def main():
    d = datasets()
    tr, va, te = d["train"], d["valid"], d["test"]
    X = list(tm.FEATURES)
    ytr, yva, yte = tr["label"].to_numpy(), va["label"].to_numpy(), te["label"].to_numpy()
    results = []

    size = ["n_total", "value_total", "n_12m"]
    for name, cols in (("logit_size_only", size), ("logit_all_signals", X)):
        m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced", C=0.5))
        m.fit(prep_linear(tr, cols), ytr)
        results.append(evaluate(name, yva, m.predict_proba(prep_linear(va, cols))[:, 1],
                                yte, m.predict_proba(prep_linear(te, cols))[:, 1], te))

    for name, extra in (("gbm_shallow", dict(num_leaves=7, min_child_samples=300, learning_rate=0.02)),
                        ("gbm_very_shallow", dict(num_leaves=4, min_child_samples=500, learning_rate=0.02)),
                        ("gbm_monotone_size", dict(num_leaves=7, min_child_samples=300, learning_rate=0.02,
                                                   monotone_constraints=[1 if f in ("n_total", "value_total", "n_12m")
                                                                         else 0 for f in X]))):
        params = dict(objective="binary", metric="auc", feature_fraction=0.8, bagging_fraction=0.8,
                      bagging_freq=1, lambda_l2=5.0, verbose=-1, seed=42, **extra)
        m = lgb.train(params, lgb.Dataset(tr[X], ytr), 4000, valid_sets=[lgb.Dataset(va[X], yva)],
                      callbacks=[lgb.early_stopping(300, verbose=False)])
        r = evaluate(name, yva, m.predict(va[X], num_iteration=m.best_iteration),
                     yte, m.predict(te[X], num_iteration=m.best_iteration), te)
        r["iterations"] = m.best_iteration
        results.append(r)

    table = pd.DataFrame(results).sort_values("valid_auc", ascending=False)
    print(table.to_string(index=False))
    (tm.MODEL_DIR / "experiments.json").write_text(table.to_json(orient="records", indent=2), encoding="utf8")


if __name__ == "__main__":
    main()
