"""Bangladesh e-GP contract awards in the Open Contracting Data Standard (OCDS 1.1).

One OCDS release per awarded lot (tags "award" + "contract"), with the buying office as buyer and
procuring entity, the winner as supplier, the award value, the signing date, the buying method mapped to the
OCDS codelist, the number of tenders received where Prohori read the contract detail page, and a link to the
official e-GP award notice.

Used by pipeline/export_ocds.py (bulk files) and by the app (one firm's awards as a release package).
Notes for data users:
  - The ocid prefix "ocds-prhr01" is a placeholder: it is not registered with the Open Contracting Partnership.
  - Supplier ids are assigned by Prohori from cleaned company names (e-GP notices before 2025 carry no company id),
    so different firms with the same name share an id.
  - Risk scores are NOT included: this is the official award record only.
"""
import hashlib
from datetime import date, datetime

PREFIX = "ocds-prhr01"
EGP_NOTICE = "https://www.eprocure.gov.bd/resources/common/ViewAwardedContracts.jsp?pkgLotId={p}&tenderid={t}"

# e-GP buying-method codes -> OCDS procurementMethod codelist (open / selective / limited / direct)
METHOD = {
    "OTM": ("open", "Open Tendering Method"),
    "OSTETM": ("open", "One Stage Two Envelope Tendering Method"),
    "LTM": ("selective", "Limited Tendering Method (enlisted firms only)"),
    "RFQ": ("limited", "Request for Quotation"),
    "RFQU": ("limited", "Request for Quotation (urgent)"),
    "RFQL": ("limited", "Request for Quotation (lump sum)"),
    "DPM": ("direct", "Direct Procurement Method"),
    "SSS": ("direct", "Single Source Selection (consultant)"),
    "QCBS": ("selective", "Quality and Cost Based Selection (consultant shortlist)"),
    "SFB": ("selective", "Selection under a Fixed Budget (consultant shortlist)"),
    "IC": ("limited", "Individual Consultant selection"),
}
CURRENCY_FIX = {"JYP": "JPY"}


def _id(kind: str, text: str) -> str:
    return f"BD-PRHR-{kind}-" + hashlib.sha1((text or "").encode("utf8")).hexdigest()[:12]


def _dt(v):
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%dT%H:%M:%S+06:00")
    if isinstance(v, date):
        return f"{v.isoformat()}T00:00:00+06:00"
    return None


def release(r: dict, received=None) -> dict:
    """One OCDS release from a row of the contracts table (+ tenders received, if known)."""
    tid, lot = str(r["tender_id"]), str(r["pkg_lot_id"])
    buyer = {"id": _id("PE", r["procuring_entity"]), "name": r["procuring_entity"]}
    supplier = {"id": _id("SUP", r["winner_key"]), "name": r["winner"]}
    if r.get("foreign_currency"):
        value = {"amount": r["foreign_amount"], "currency": CURRENCY_FIX.get(r["foreign_currency"], r["foreign_currency"])}
    elif r.get("value_bdt") is not None:
        value = {"amount": round(float(r["value_bdt"]), 2), "currency": "BDT"}
    else:
        value = None
    m, m_detail = METHOD.get(r["method"], (None, r["method"]))
    signed = _dt(r["signed_date"])
    tender = {"id": tid, "title": r["title"], "procuringEntity": buyer,
              "procurementMethodDetails": f"{r['method']}: {m_detail}" if r["method"] else None}
    if m:
        tender["procurementMethod"] = m
    if r.get("advertised_at"):
        tender["tenderPeriod"] = {"startDate": _dt(r["advertised_at"])}
    if received is not None:
        tender["numberOfTenderers"] = int(received)
    award = {"id": f"{tid}-{lot}", "title": r["title"], "status": "active", "suppliers": [supplier],
             "documents": [{"id": f"{tid}-{lot}-noa", "documentType": "awardNotice", "title": "e-GP award notice",
                            "url": EGP_NOTICE.format(p=lot, t=tid), "format": "text/html"}]}
    contract = {"id": f"{tid}-{lot}-c", "awardID": award["id"], "status": "active"}
    if value:
        award["value"] = value
        contract["value"] = value
    if signed:
        contract["dateSigned"] = signed
    out = {
        "ocid": f"{PREFIX}-{tid}", "id": f"{tid}-{lot}-award", "date": signed or _dt(r.get("fetched_at")),
        "tag": ["award", "contract"], "initiationType": "tender", "language": "en",
        "parties": [
            {**buyer, "roles": ["buyer", "procuringEntity"],
             "address": {"region": r.get("district") or None, "countryName": "Bangladesh"},
             "details": {"ministry": r.get("ministry")}},
            {**supplier, "roles": ["supplier"], "address": {"countryName": "Bangladesh"},
             "details": {"jointVenture": bool(r.get("is_jv"))}},
        ],
        "buyer": buyer, "tender": {k: v for k, v in tender.items() if v is not None},
        "awards": [award], "contracts": [contract],
    }
    if out["parties"][0]["address"]["region"] is None:
        del out["parties"][0]["address"]["region"]
    return out


def package(releases: list, uri: str) -> dict:
    return {
        "uri": uri, "version": "1.1", "publishedDate": _dt(datetime.now()),
        "publisher": {"name": "Prohori (independent; republished from the Bangladesh e-GP portal)",
                      "uri": "https://prohori.safeshare.co"},
        "publicationPolicy": "https://github.com/Eusha122/Prohori#open-data-ocds",
        "releases": releases,
    }
