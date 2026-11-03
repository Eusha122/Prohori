<p align="center">
  <img src="brand/png/prohori-logo-light.png" alt="প্রহরী — Prohori" width="420">
</p>

# প্রহরী · Prohori — Public Procurement Watch

**An AI watchdog for Bangladesh's public procurement.** Prohori reads the contract awards that government
offices publish on the national e-GP portal ([eprocure.gov.bd](https://www.eprocure.gov.bd)) and highlights
patterns worth a closer look — explained in plain Bangla and English.

> Built for the **International AI Builders Congress 2026** · Idea to Unicorn → CivicSphere AI → *Transparent Government*.

![Prohori home page](docs/screenshots/home.png)

## Why

- Government offices award roughly **1.2 lakh tenders a year**, worth about **Tk 1 lakh crore**. Every award is
  public on e-GP by law — but there are close to **9 lakh** of them, far too many to review by hand.
- Transparency International Bangladesh found that the **top 5% of contractors won 61% of e-GP contract value**.
- AI watchdogs on procurement data already work elsewhere (Brazil's *ALICE*, Ukraine's *DOZORRO*).
  Prohori brings the idea to Bangladesh, on Bangladesh's own open data.

## What it does (prototype)

| Feature | Status |
|---|---|
| Polite, resumable collection of all public award notices (2011 → today) and the debarment list | ✅ |
| Cleaning, de-duplication and company-name matching (exact, near-exact, joint-venture partners) | ✅ |
| Rule-based risk patterns: one company dominating an office, direct/single-source buying, officially debarred winners, shared-name warnings | ✅ |
| Web app: search, company pages, office pages, risk-pattern list, debarred firms, largest contracts — bilingual, mobile-friendly | ✅ |
| Trained risk model (gradient boosting) with a time-split backtest against later debarments | 🚧 after full data collection |
| Company-network detection (shared owners / addresses from contract detail pages) | 🚧 |
| Bangla explanations and Q&A with Amazon Bedrock (Nova) | 🚧 |

**Flags are patterns for review, not accusations.** A high share of contracts can have innocent reasons;
Prohori never labels anyone corrupt and a human always decides. Companies are named as "debarred" only when the
government itself has debarred them.

## Project structure

```
collector/   Node + Playwright collectors for e-GP public pages (resumable, rate-limited)
pipeline/    Python: build the DuckDB database, match debarred firms, compute risk features
app/         FastAPI JSON API + static front end (HTML/CSS/JS, no build step)
brand/       Logo sources (SVG) and rendered PNGs
docs/        Business model PDF and screenshots
data/        Raw and processed data — not committed (see data/README.md)
```

## Run it locally

Requirements: Python 3.11+, Node.js 18+.

```bash
# 1. Python environment
python -m venv .venv
.venv\Scripts\activate            # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt

# 2. Collect data from the public e-GP portal (takes many hours for the full history)
cd collector
npm install
npm run setup                      # downloads Playwright's Chromium
npm run debarment                  # debarment list (~10 minutes)
npm run collect                    # award notices; safe to stop and restart, it resumes
cd ..
#   Windows shortcut: collector\START_COLLECTING.bat runs 4 collectors over different page ranges.

# 3. Build the database
python pipeline/build_db.py
python pipeline/match_debarred.py
python pipeline/build_features.py

# 4. Start the app, then open http://localhost:8000
python -m uvicorn app.main:app --port 8000
#   Windows shortcut: START_APP.bat
```

Stop the app before re-running the pipeline (the pipeline needs write access to `data/prohori.duckdb`).

## Data and responsible use

- **Source:** public, login-free pages of the Bangladesh e-GP portal (contract award notices and the debarment
  list). No private or personal data is collected beyond what the government publishes.
- **Collection is deliberately gentle:** one request at a time per collector with delays and automatic back-off.
- **Matching caveat:** older contracts have no company ID, so firms are matched by name. Different firms can share
  a name; the app warns when a name appears in many districts. Address- and ID-based matching is in progress.
- Prohori is an **independent project**, not affiliated with BPPA or any government office.

## Tech

Python · DuckDB · pandas · RapidFuzz · FastAPI · Playwright · vanilla HTML/CSS/JS · Amazon Bedrock (planned).
