# Contributing to Prohori

Thank you for helping. Prohori is an independent, open-source watchdog for Bangladesh public procurement. Anyone can
help, from Dhaka or from anywhere in the world. You do not need to ask first: pick a task, open an issue or a pull
request, and we will review it.

**Credit:** every merged contribution is credited by your public GitHub handle. We never list anyone as an advisor or
partner unless they say so publicly themselves.

## Starter tasks (good first issues)

| Task | Skills | Why it matters |
|---|---|---|
| **OCDS exporter**: write `pipeline/export_ocds.py` that turns the `contracts` table into OCDS release packages | Python, JSON | Lets other tools and countries reuse Prohori's data |
| **Upazila mapping**: extract upazila names from contract titles and office names | Python, regex, Bangla place names | Lets the district pages go down to upazila level |
| **Bangla procurement glossary**: plain Bangla for OTM, LTM, RFQ, debarment, performance security, and more | Bangla writing | Better AI answers and page text |
| **Test the AI assistant**: write 10 Bangla or English questions with the correct answer from the page | Any | Builds our public test set for answer quality |
| **District name cleaning**: find spellings that `pipeline/geo.py` misses | Python | More accurate district pages |
| **Accessibility**: check pages with a screen reader and on small phones | HTML/CSS | Prohori must work for everyone |

## Rules

1. **Public data only.** Never add private or leaked data, personal phone numbers, home addresses or ID numbers.
2. **No accusations.** Code and text must call patterns "risk signals for review", never "corrupt" or "fraud".
3. **Be polite to the source.** Any new data collector must read slowly, cache results, and never bypass logins.
4. **Keep the rule:** nothing may let a paying customer change, hide or lower a risk score.

## Running it locally

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
START_APP.bat            (or: .venv\Scripts\python -m uvicorn app.main:app --port 8000)
```

The AI assistant needs Amazon Bedrock keys in a local `.env` file (never commit it). Everything else works without them.
