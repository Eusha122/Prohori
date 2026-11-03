"""Compute summary tables and first rule-based risk flags (no ML) for the app.

Run after build_db.py and match_debarred.py. Creates in data/prohori.duckdb:
  office_winner     wins per (office, company) with share of the office's contracts
  office_summary    one row per buying office: size, top winner, concentration (HHI)
  company_summary   one row per company: size, reach, method mix, dominance, debarment
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "prohori.duckdb"

# A company "dominates" an office when it wins at least this share of the office's
# contracts, and the office has awarded enough contracts for the share to mean something.
DOMINANCE_SHARE = 0.40
MIN_OFFICE_CONTRACTS = 20
# Names that show up in many districts may be several different firms with one name.
AMBIGUOUS_DISTRICTS = 9

SQL = f"""
CREATE OR REPLACE TABLE office_winner AS
WITH o AS (
  SELECT procuring_entity, count(*) AS office_n, sum(value_bdt) AS office_value
  FROM contracts GROUP BY 1)
SELECT c.procuring_entity, c.winner_key,
       count(*) AS n, sum(c.value_bdt) AS value_bdt,
       count(*) / any_value(o.office_n) AS share_n,
       sum(c.value_bdt) / nullif(any_value(o.office_value), 0) AS share_value,
       any_value(o.office_n) AS office_n
FROM contracts c JOIN o USING (procuring_entity)
GROUP BY 1, 2;

CREATE OR REPLACE TABLE office_summary AS
SELECT ow.procuring_entity,
       any_value(c.ministry) AS ministry,
       mode(c.district) AS district,
       any_value(ow.office_n) AS n_contracts,
       (SELECT sum(value_bdt) FROM contracts x WHERE x.procuring_entity = ow.procuring_entity) AS value_bdt,
       count(DISTINCT ow.winner_key) AS n_winners,
       arg_max(ow.winner_key, ow.n) AS top_winner_key,
       max(ow.share_n) AS top_share_n,
       sum(ow.share_value * ow.share_value) AS hhi_value
FROM office_winner ow
JOIN (SELECT procuring_entity, any_value(ministry) AS ministry, mode(district) AS district
      FROM contracts GROUP BY 1) c USING (procuring_entity)
GROUP BY ow.procuring_entity;

CREATE OR REPLACE TABLE company_summary AS
WITH base AS (
  SELECT winner_key,
         mode(winner_clean) AS name,
         count(*) AS n_contracts,
         sum(value_bdt) AS value_bdt,
         count(DISTINCT procuring_entity) AS n_offices,
         count(DISTINCT district) AS n_districts,
         min(signed_date) AS first_contract,
         max(signed_date) AS last_contract,
         avg(CASE WHEN method IN ('DPM', 'SSS') THEN 1 ELSE 0 END) AS share_direct,
         avg(CASE WHEN method = 'LTM' THEN 1 ELSE 0 END) AS share_limited,
         bool_or(is_jv) AS any_jv
  FROM contracts GROUP BY 1),
dom AS (
  SELECT winner_key, count(*) AS n_dominated_offices, max(share_n) AS max_office_share
  FROM office_winner
  WHERE share_n >= {DOMINANCE_SHARE} AND office_n >= {MIN_OFFICE_CONTRACTS}
  GROUP BY 1),
deb AS (
  SELECT company_key AS winner_key, min(debar_from) AS first_debar_from,
         max(debar_to) AS last_debar_to, count(*) AS n_debarments,
         any_value(debarred_by) AS debarred_by, any_value(reason) AS reason
  FROM debarments GROUP BY 1)
SELECT b.*,
       coalesce(d.n_dominated_offices, 0) AS n_dominated_offices,
       d.max_office_share,
       deb.first_debar_from, deb.last_debar_to, coalesce(deb.n_debarments, 0) AS n_debarments,
       deb.debarred_by, deb.reason AS debar_reason,
       b.n_districts >= {AMBIGUOUS_DISTRICTS} AS name_may_be_shared
FROM base b
LEFT JOIN dom d USING (winner_key)
LEFT JOIN deb USING (winner_key);
"""


def main():
    con = duckdb.connect(str(DB_PATH))
    con.execute(SQL)
    for t in ("office_winner", "office_summary", "company_summary"):
        print(f"{t:16s}: {con.execute(f'SELECT count(*) FROM {t}').fetchone()[0]:,} rows")
    print("companies dominating at least one office:",
          con.execute("SELECT count(*) FROM company_summary WHERE n_dominated_offices > 0").fetchone()[0])
    print("debarred companies found in contracts   :",
          con.execute("SELECT count(*) FROM company_summary WHERE n_debarments > 0").fetchone()[0])
    con.close()


if __name__ == "__main__":
    main()
