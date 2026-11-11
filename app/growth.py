"""Waitlist sign-ups and a privacy-friendly usage counter (market validation without outreach).

- Sign-ups: people join a waitlist for a planned paid plan (Contractor Pro, Lender Check, Institution) or a
  free digest. Nothing is sold and no money is taken. Stored in data/growth.sqlite.
- Counter: counts page views, searches and chat questions per day. No cookies, no IP addresses stored.
  The browser sends a random visitor id (kept in its own storage) and its time zone, so we can count
  unique visitors and visits from outside Bangladesh (a small, honest diaspora signal).
"""
import re
import sqlite3
import threading
import time
from collections import defaultdict, deque
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "growth.sqlite"

PLANS = {"pro", "lender", "institution", "digest", "alerts", "notify"}
ROLES = {"contractor", "bank", "journalist", "nrb", "citizen", "student", "government", "ngo", "other"}
EVENTS = {"view", "search", "chat", "report", "signup_open"}
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[A-Za-z]{2,}$")
PHONE = re.compile(r"^\+?[0-9 \-]{8,16}$")


class Growth:
    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS signups (
                id INTEGER PRIMARY KEY, created REAL, plan TEXT, role TEXT, contact TEXT, name TEXT,
                place TEXT, abroad INTEGER, target TEXT, price_variant TEXT, note TEXT);
            CREATE TABLE IF NOT EXISTS events (
                day TEXT, event TEXT, page TEXT, abroad INTEGER, n INTEGER,
                PRIMARY KEY (day, event, page, abroad));
            CREATE TABLE IF NOT EXISTS visitors (day TEXT, vid TEXT, abroad INTEGER, PRIMARY KEY (day, vid));
        """)
        self.lock = threading.Lock()
        self.recent = defaultdict(deque)   # ip -> sign-up times, to stop form spam

    def signup(self, d: dict, ip: str) -> dict:
        plan, role = d.get("plan", ""), d.get("role", "")
        contact = (d.get("contact") or "").strip()[:120]
        if plan not in PLANS:
            raise ValueError("Unknown plan.")
        if role not in ROLES:
            raise ValueError("Please choose who you are.")
        if not (EMAIL.match(contact) or PHONE.match(contact)):
            raise ValueError("Please give a valid email or mobile number.")
        now = time.time()
        with self.lock:
            q = self.recent[ip]
            while q and now - q[0] > 3600:
                q.popleft()
            if len(q) >= 10:
                raise ValueError("Too many sign-ups from this connection. Please try later.")
            q.append(now)
            dup = self.db.execute("SELECT 1 FROM signups WHERE contact = ? AND plan = ? AND target = ?",
                                  [contact.lower(), plan, (d.get("target") or "")[:200]]).fetchone()
            if not dup:
                self.db.execute(
                    "INSERT INTO signups (created, plan, role, contact, name, place, abroad, target, price_variant, note)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [now, plan, role, contact.lower(), (d.get("name") or "").strip()[:80],
                     (d.get("place") or "").strip()[:80], 1 if d.get("abroad") else 0,
                     (d.get("target") or "")[:200], (d.get("price_variant") or "")[:10],
                     (d.get("note") or "").strip()[:500]])
                self.db.commit()
        return {"ok": True, "already": bool(dup)}

    def track(self, d: dict) -> None:
        event, page = d.get("event", ""), str(d.get("page", ""))[:30]
        if event not in EVENTS or not re.fullmatch(r"[a-z0-9_]*", page):
            return
        abroad = 1 if d.get("abroad") else 0
        day = date.today().isoformat()
        vid = re.sub(r"[^a-z0-9]", "", str(d.get("vid", "")).lower())[:32]
        with self.lock:
            self.db.execute("INSERT INTO events VALUES (?, ?, ?, ?, 1) ON CONFLICT DO UPDATE SET n = n + 1",
                            [day, event, page, abroad])
            if vid and event == "view":
                self.db.execute("INSERT OR IGNORE INTO visitors VALUES (?, ?, ?)", [day, vid, abroad])
            self.db.commit()

    def numbers(self) -> dict:
        """Open numbers shown on the public 'Open numbers' page. Totals only; no contact details ever."""
        with self.lock:
            q = lambda sql, p=(): self.db.execute(sql, p).fetchall()  # noqa: E731
            ev = {(e, a): n for e, a, n in q("SELECT event, abroad, sum(n) FROM events GROUP BY 1, 2")}
            vis = q("SELECT count(DISTINCT vid), count(DISTINCT CASE WHEN abroad = 1 THEN vid END) FROM visitors")[0]
            first = q("SELECT min(day) FROM events")[0][0]
            by_plan = dict(q("SELECT plan, count(*) FROM signups GROUP BY 1"))
            by_role = dict(q("SELECT role, count(*) FROM signups GROUP BY 1"))
            abroad_signups = q("SELECT count(*) FROM signups WHERE abroad = 1")[0][0]
            price = {v: n for v, n in q("SELECT price_variant, count(*) FROM signups "
                                        "WHERE plan = 'pro' AND price_variant != '' GROUP BY 1")}
            opens = {v: n for v, n in q("SELECT page, sum(n) FROM events WHERE event = 'signup_open' GROUP BY 1")}
            days = q("SELECT day, count(DISTINCT vid) FROM visitors GROUP BY 1 ORDER BY 1 DESC LIMIT 30")
        tot = lambda e: ev.get((e, 0), 0) + ev.get((e, 1), 0)  # noqa: E731
        return {
            "since": first, "visitors": vis[0], "visitors_abroad": vis[1],
            "page_views": tot("view"), "searches": tot("search"), "chat_questions": tot("chat"),
            "reports_opened": tot("report"), "signups": sum(by_plan.values()), "signups_by_plan": by_plan,
            "signups_by_role": by_role, "signups_abroad": abroad_signups, "pro_price_test": price,
            "pro_form_opens": opens, "daily_visitors": [{"day": d, "visitors": n} for d, n in reversed(days)],
        }
