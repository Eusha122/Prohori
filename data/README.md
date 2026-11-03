# data/

This folder is not committed (it is several hundred MB and fully re-creatable).

| Path | Created by | Contents |
|---|---|---|
| `raw/noa/` | `collector/collect_noa.js` | Contract award notices from the e-GP portal, one JSON object per line (`noa*.jsonl`), plus bookmark files (`pages_done*.txt`) |
| `raw/debarment/debarment.jsonl` | `collector/collect_debarment.js` | The public e-GP debarment list |
| `prohori.duckdb` | `pipeline/*.py` | Cleaned database used by the app |

Source: Bangladesh national e-GP portal, https://www.eprocure.gov.bd (public pages, no login).
