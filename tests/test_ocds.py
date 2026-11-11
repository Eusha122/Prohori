"""Tests for the OCDS export and the country-neutral checks.

The schema test uses the official OCDS 1.1.5 release schema saved by pipeline/export_ocds.py
(data/ocds/schema/); it is skipped if that file is not there.
"""
import gzip
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.ocds import METHOD, release  # noqa: E402
from pipeline import ocds_checks  # noqa: E402

ROW = {"tender_id": 918061, "pkg_lot_id": 1, "title": "Road repair", "ministry": "LGD", "procuring_entity": "LGED, X",
       "method": "OTM", "district": "Dhaka", "signed_date": datetime(2024, 1, 2), "advertised_at": datetime(2023, 12, 1),
       "winner": "Engineers House Ltd", "winner_key": "engineers house", "is_jv": False, "value_bdt": 25700000.0,
       "foreign_currency": None, "foreign_amount": None, "fetched_at": datetime(2026, 11, 1)}


def test_release_fields():
    r = release(ROW, received=4)
    assert r["ocid"] == "ocds-prhr01-918061"
    assert r["tender"]["procurementMethod"] == "open"
    assert r["tender"]["numberOfTenderers"] == 4
    assert r["awards"][0]["value"] == {"amount": 25700000.0, "currency": "BDT"}
    assert r["awards"][0]["documents"][0]["url"].startswith("https://www.eprocure.gov.bd/")
    assert "risk" not in json.dumps(r).lower()           # official facts only, never risk scores


def test_every_egp_method_maps_to_ocds_codelist():
    assert {m for m, _ in METHOD.values()} <= {"open", "selective", "limited", "direct"}
    assert METHOD["DPM"][0] == "direct" and METHOD["LTM"][0] == "selective"


def test_release_valid_against_official_schema():
    p = ROOT / "data" / "ocds" / "schema" / "release-schema.json"
    if not p.exists():
        pytest.skip("official OCDS schema not downloaded (run pipeline/export_ocds.py)")
    from jsonschema import Draft4Validator
    errors = list(Draft4Validator(json.loads(p.read_text(encoding="utf8"))).iter_errors(release(ROW, 4)))
    assert not errors, [e.message for e in errors]


def test_checks_run_on_any_ocds_file(tmp_path):
    """Office dominance, direct share and impossible-date handling, on a tiny made-up OCDS file."""
    lines = []
    for i in range(40):
        lines.append({"ocid": f"x-{i}", "date": "2024-01-01T00:00:00Z", "buyer": {"name": "Office A"},
                      "tender": {"procurementMethod": "direct" if i < 4 else "open", "numberOfTenderers": 1 if i < 10 else 3,
                                 "tenderPeriod": {"startDate": "2024-01-10T00:00:00Z", "endDate": "2024-01-05T00:00:00Z"}},
                      "awards": [{"status": "active", "suppliers": [{"name": "Firm 1" if i < 30 else f"Firm {i}"}],
                                  "value": {"amount": 100, "currency": "XYZ"}}]})
    f = tmp_path / "t.jsonl.gz"
    with gzip.open(f, "wt", encoding="utf8") as fh:
        fh.write("\n".join(json.dumps(x) for x in lines))
    r = ocds_checks.check({"id": "t", "country": "Test", "source": "", "url": "", "files": [f]})["checks"]
    assert r["dominance"]["flagged"] == 1 and r["dominance"]["examples"][0]["share"] == 0.75
    assert r["direct"]["share"] == 0.1
    assert r["single_bid"]["share"] == 0.25
    assert r["short_window"]["available"] is False and r["short_window"]["data_quality"] is True
