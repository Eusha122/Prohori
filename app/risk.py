"""AI risk scores for the app: loads entity_risk + the saved logistic model once, and turns model
contributions into plain-language reasons ("higher than 97% of active firms").

risk_pct (from train_model.py) is the entity's percentile rank among all active entities
(1.0 = highest). We also rank each entity against firms of similar size (deciles of contracts
won), because size alone is a strong predictor and users want to know what is unusual beyond it.
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "models"

HEAVY_TAILED = ["n_total", "n_12m", "value_total", "value_12m", "avg_value", "max_value", "n_offices",
                "n_districts", "n_ministries", "days_active", "days_since_last", "med_ad_to_sign",
                "n_dominated", "n_offices_12m", "growth_12m", "value_jump"]
SIZE = {"n_total", "n_12m", "value_total", "value_12m", "avg_value", "max_value"}

# feature -> (sentence label, value format). Formats: n = count, tk = taka, pct = share, x = ratio, d = days
LABELS = {
    "n_total": ("Contracts won (all time)", "n"),
    "n_12m": ("Contracts won in the last 12 months", "n"),
    "growth_12m": ("Growth in contracts vs the year before", "x"),
    "value_total": ("Total contract value", "tk"),
    "value_12m": ("Contract value in the last 12 months", "tk"),
    "avg_value": ("Average contract size", "tk"),
    "max_value": ("Largest contract", "tk"),
    "n_offices": ("Number of government offices it wins from", "n"),
    "n_districts": ("Number of districts it works in", "n"),
    "n_ministries": ("Number of ministries it works for", "n"),
    "share_direct": ("Contracts given by direct / single-source buying", "pct"),
    "share_ltm": ("Contracts by limited tendering", "pct"),
    "share_rfq": ("Contracts by request for quotation", "pct"),
    "share_otm": ("Contracts by open tendering", "pct"),
    "share_jv": ("Contracts won as a joint venture", "pct"),
    "days_active": ("Time since its first contract", "d"),
    "days_since_last": ("Time since its last contract", "d"),
    "med_ad_to_sign": ("Typical days from advertisement to contract", "d"),
    "share_fast": ("Contracts signed within 21 days of advertisement", "pct"),
    "top_office_share": ("Highest share of one office's contracts", "pct"),
    "n_dominated": ("Offices where it wins 40%+ of contracts", "n"),
    "top_office_concentration": ("Share of its own work from one office", "pct"),
    "share_lged": ("Contracts from local-government engineering (LGED)", "pct"),
    "share_roads": ("Contracts from roads & highways", "pct"),
    "n_offices_12m": ("Offices it won from in the last 12 months", "n"),
    "new_office_share_12m": ("Last year's offices that were new to it", "pct"),
    "value_jump": ("Recent contract size vs its usual size", "x"),
    "share_road": ("Road works", "pct"), "share_bridge": ("Bridge / culvert works", "pct"),
    "share_building": ("Building works", "pct"), "share_repair": ("Repair / maintenance works", "pct"),
    "share_water": ("Water / drainage works", "pct"), "share_electric": ("Electrical works", "pct"),
    "share_supply": ("Supply / purchase contracts", "pct"), "share_service": ("Service contracts", "pct"),
}


LABELS_BN = {
    "n_total": "মোট জেতা চুক্তি", "n_12m": "গত ১২ মাসে জেতা চুক্তি", "growth_12m": "আগের বছরের তুলনায় চুক্তি বৃদ্ধি",
    "value_total": "মোট চুক্তিমূল্য", "value_12m": "গত ১২ মাসের চুক্তিমূল্য", "avg_value": "গড় চুক্তির আকার",
    "max_value": "সবচেয়ে বড় চুক্তি", "n_offices": "যত সরকারি অফিস থেকে কাজ পায়", "n_districts": "যত জেলায় কাজ করে",
    "n_ministries": "যত মন্ত্রণালয়ের কাজ করে", "share_direct": "সরাসরি / একক উৎসে ক্রয়ের চুক্তি",
    "share_ltm": "সীমিত দরপত্রের চুক্তি", "share_rfq": "দরপ্রস্তাব (আরএফকিউ) চুক্তি", "share_otm": "উন্মুক্ত দরপত্রের চুক্তি",
    "share_jv": "যৌথ উদ্যোগে জেতা চুক্তি", "days_active": "প্রথম চুক্তির পর থেকে সময়", "days_since_last": "শেষ চুক্তির পর থেকে সময়",
    "med_ad_to_sign": "বিজ্ঞাপন থেকে চুক্তি পর্যন্ত সাধারণ সময়", "share_fast": "বিজ্ঞাপনের ২১ দিনের মধ্যে সই হওয়া চুক্তি",
    "top_office_share": "একটি অফিসের চুক্তিতে সর্বোচ্চ অংশ", "n_dominated": "যেসব অফিসে ৪০%+ চুক্তি পায়",
    "top_office_concentration": "নিজের কাজের কত অংশ একটি অফিস থেকে", "share_lged": "এলজিইডি থেকে পাওয়া চুক্তি",
    "share_roads": "সড়ক ও জনপথ থেকে পাওয়া চুক্তি", "n_offices_12m": "গত ১২ মাসে যত অফিস থেকে কাজ পেয়েছে",
    "new_office_share_12m": "গত বছরের নতুন অফিসের অংশ", "value_jump": "সাম্প্রতিক চুক্তির আকার বনাম সাধারণ আকার",
    "share_road": "সড়কের কাজ", "share_bridge": "সেতু / কালভার্টের কাজ", "share_building": "ভবনের কাজ",
    "share_repair": "মেরামত / রক্ষণাবেক্ষণের কাজ", "share_water": "পানি / ড্রেনেজের কাজ", "share_electric": "বৈদ্যুতিক কাজ",
    "share_supply": "সরবরাহ / ক্রয়ের চুক্তি", "share_service": "সেবার চুক্তি",
}


def fmt(v, kind):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    if kind == "pct":
        return f"{v:.0%}"
    if kind == "x":
        return f"{v:.1f}×"
    if kind == "d":
        return f"{v / 365:.1f} years" if v >= 365 else f"{v:.0f} days"
    if kind == "tk":
        if v >= 1e7:
            return f"Tk {v / 1e7:,.2f} crore" if v < 1e9 else f"Tk {v / 1e7:,.0f} crore"
        if v >= 1e5:
            return f"Tk {v / 1e5:,.1f} lakh"
        return f"Tk {v:,.0f}"
    return f"{v:,.0f}"


def band(top):
    """Review priority from the overall 'top X%' position."""
    if top <= 1:
        return "very_high", "Very high"
    if top <= 5:
        return "high", "High"
    if top <= 15:
        return "elevated", "Elevated"
    return "typical", "Typical"


class RiskIndex:
    def __init__(self, con):
        self.df = con.execute("SELECT * FROM entity_risk").df()
        self.metrics = json.loads((MODEL_DIR / "metrics.json").read_text(encoding="utf8"))
        p = MODEL_DIR / "detail_eval.json"
        self.detail_eval = json.loads(p.read_text(encoding="utf8")) if p.exists() else None
        model = joblib.load(MODEL_DIR / "risk_logit.joblib")
        self.cols = list(model[0].feature_names_in_)
        x = self.df[self.cols].astype(float).fillna(0).clip(lower=0)
        for c in HEAVY_TAILED:
            x[c] = np.log1p(x[c])
        z = model[0].transform(x)
        coef = model[-1].coef_[0]
        self.contrib = z * coef
        self.coef = coef
        self.z = z
        d = self.df
        d["top_pct"] = (1 - d["risk_pct"]) * 100
        d["size_decile"] = pd.qcut(d["n_total"].rank(method="first"), 10, labels=False)
        d["top_pct_size"] = (1 - d.groupby("size_decile")["risk_pct"].rank(pct=True)) * 100
        # percentile of each raw feature among active firms, for "higher than X% of firms"
        self.feat_pct = d[self.cols].rank(pct=True)
        self.pos = {e: i for i, e in enumerate(d["entity"])}
        self.n = len(d)

    def reasons(self, i, k=3, exclude_size=False):
        """Top signals that raise this entity's score: feature high AND high = riskier."""
        out = []
        for j in np.argsort(-self.contrib[i]):
            f = self.cols[j]
            if self.contrib[i, j] <= 0.15 or self.coef[j] <= 0 or self.z[i, j] <= 0:
                continue
            if exclude_size and f in SIZE:
                continue
            label, kind = LABELS[f]
            raw = self.df[f].iat[i]
            out.append({"feature": f, "label": label, "label_bn": LABELS_BN.get(f, label), "kind": kind,
                        "raw": None if raw is None or (isinstance(raw, float) and np.isnan(raw)) else float(raw),
                        "value": fmt(raw, kind),
                        "higher_than": min(99, int(float(self.feat_pct[f].iat[i]) * 100)),
                        "size_related": f in SIZE})
            if len(out) == k:
                break
        return out

    def entity_row(self, i):
        r = self.df.iloc[i]
        top = max(0.1, round(float(r["top_pct"]), 1))
        key, label = band(top)
        return {"entity": r["entity"], "winner_key": r["winner_key"], "division": r["division"],
                "name": r["name"], "top_pct": top, "top_pct_size": max(1, round(float(r["top_pct_size"]))),
                "band": key, "band_label": label, "n_contracts": int(r["n_total"]),
                "value_bdt": float(r["value_total"] or 0),
                "reasons": self.reasons(i), "behaviour_reasons": self.reasons(i, exclude_size=True)}

    def for_company(self, winner_key):
        idx = self.df.index[self.df["winner_key"] == winner_key]
        rows = [self.entity_row(i) for i in idx]
        return sorted(rows, key=lambda r: r["top_pct"])

    def watchlist(self, view="overall", division=None, limit=100):
        d = self.df
        if division:
            d = d[d["division"] == division]
        col = "top_pct_size" if view == "size" else "top_pct"
        if view == "size":
            d = d[d["n_total"] >= 10]          # tiny firms: too little history to call "unusual"
        idx = d.sort_values(col).index[:limit]
        return [self.entity_row(i) for i in idx]

    def summary(self):
        tops = self.df["top_pct"]
        return {"scored": self.n, "very_high": int((tops <= 1).sum()), "high": int((tops <= 5).sum()),
                "divisions": sorted(self.df["division"].dropna().unique().tolist())}

    def model_report(self):
        keep = ("test_rows", "test_positives", "base_rate", "roc_auc", "roc_auc_95ci", "top_1pct", "top_5pct",
                "top_10pct", "auc_within_size_deciles", "auc_per_snapshot", "size_only_baseline",
                "caught_in_advance", "test", "train")
        m = self.metrics
        return {"horizon_months": m.get("horizon_months"), "model": m.get("model"),
                "main_test": {k: m["main_test"][k] for k in keep if k in m["main_test"]},
                "stability_fold": {k: m["stability_fold"][k] for k in keep if k in m["stability_fold"]},
                "weights": m.get("logistic_weights"), "detail_eval": self.detail_eval, "scored": self.n}
