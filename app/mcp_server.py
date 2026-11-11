"""Prohori MCP server: lets any AI assistant that speaks the Model Context Protocol query Prohori's public data.

Endpoint (Streamable HTTP, stateless, JSON responses): https://prohori.safeshare.co/mcp
It is served by the same FastAPI app (app/main.py), so it reads the same data and follows the same limits.
All tools are read-only. Every answer carries Prohori's notice: risk patterns and scores are signals for human
review, never proof of wrongdoing.

Local use (stdio), for people who built the database themselves:
    python -m app.mcp_server
"""
import json

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

NOTICE = ("Prohori is an independent public-data watchdog, not a government website. Risk patterns and AI scores "
          "are signals for human review, not proof of wrongdoing; most firms ranked high are never debarred. "
          "A debarment is an official government decision. Check facts at the linked official source "
          "(eprocure.gov.bd). Do not describe any firm or person as corrupt or guilty.")

INSTRUCTIONS = f"""Prohori covers Bangladesh government contracts published on the national e-GP portal (Dec 2011 to
today, about 893,000 awards), the government's debarment (ban) list, an AI review priority for active firms (tested
against later debarments), Bangladesh's procurement law (Public Procurement Rules 2025, Act 2006 and amendments),
and the same rule-based checks run on other countries' open contracting (OCDS) data.
Typical flow: search_firms_and_offices -> get_company (use the returned key) -> check_ban_list / make_brief.
{NOTICE}"""

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)


def _safe(fn):
    """Turn "not found" errors from the app into a clear answer the AI assistant can act on."""
    import functools

    @functools.wraps(fn)
    def run(*a, **k):
        try:
            return fn(*a, **k)
        except Exception as e:        # fastapi.HTTPException carries status_code + detail
            if getattr(e, "status_code", None) == 404:
                return {"error": f"{e.detail}. Use search_firms_and_offices to find the exact key or name first."}
            raise
    return run


def _plain(x):
    """Dates and numpy values -> JSON-safe values."""
    return json.loads(json.dumps(x, default=str))


def create_mcp(api, allowed_hosts=("prohori.safeshare.co",)):
    """Build the MCP server on top of the app's own functions (`api` is the app.main module)."""
    mcp = MCPServer(name="Prohori", title="Prohori — Bangladesh public procurement watch",
                    description="Bangladesh government contracts, debarments, AI review priority and procurement law.",
                    instructions=INSTRUCTIONS, website_url="https://prohori.safeshare.co", version="1.0")

    @mcp.tool(annotations=READ_ONLY)
    def search_firms_and_offices(query: str) -> dict:
        """Find companies (contract winners) and government buying offices by name. Returns each company's `key`,
        which the other tools need."""
        r = api.search(query)
        return _plain({"companies": r["companies"], "offices": r["offices"], "notice": NOTICE})

    @mcp.tool(annotations=READ_ONLY)
    @_safe
    def get_company(key: str) -> dict:
        """One company's public contract record: totals, rule-based risk patterns, official debarment, AI review
        priority with its reasons, the offices it wins from, contracts per year, and recent contracts with links to
        the official e-GP award notices. `key` comes from search_firms_and_offices."""
        r = api.company(key)
        for x in r["recent"]:
            x["egp_notice"] = api.EGP_NOTICE.format(p=x["pkg_lot_id"], t=x["tender_id"])
        r["page"] = f"https://prohori.safeshare.co/#/company/{key}"
        r["notice"] = NOTICE
        return _plain(r)

    @mcp.tool(annotations=READ_ONLY)
    @_safe
    def get_office(name: str) -> dict:
        """One government buying office: its contracts, how many companies win there, and who wins most."""
        r = api.office(name)
        r["page"] = f"https://prohori.safeshare.co/#/office/{name}"
        r["notice"] = NOTICE
        return _plain(r)

    @mcp.tool(annotations=READ_ONLY)
    def check_ban_list(company_name: str) -> dict:
        """Search the Bangladesh government's e-GP debarment (ban) list by company name. Returns the official
        records (who banned the firm, from when to when, the reason on record). Names are matched by spelling, so
        different firms can share a name."""
        return _plain({"records": api.ban_search(company_name), "source": "https://www.eprocure.gov.bd/resources/"
                       "common/DebarmentRpt.jsp", "notice": NOTICE})

    @mcp.tool(annotations=READ_ONLY)
    def ai_watchlist(view: str = "overall", division: str = "", limit: int = 20) -> dict:
        """Active firms Prohori's AI ranks first for human review. view = "overall" or "size" (unusual for their
        size). division = optional Bangladesh division (e.g. "Dhaka"). A review list, not a list of guilty firms."""
        r = api.watchlist(view if view in ("overall", "size") else "overall", division or None, max(1, min(50, limit)))
        r["notice"] = NOTICE
        return _plain(r)

    @mcp.tool(annotations=READ_ONLY)
    def model_accuracy() -> dict:
        """How accurate Prohori's AI review priority was when tested on past data it never saw (backtest against
        later debarments), including where it did NOT beat a simple size rule."""
        return _plain(api.model_report())

    @mcp.tool(annotations=READ_ONLY)
    def search_procurement_law(query: str) -> dict:
        """Search Bangladesh's procurement law (Public Procurement Rules 2025, Public Procurement Act 2006 and the
        2025 / 2026 amendments). Returns the most relevant pages with an English summary and a link to the page of
        the official BPPA PDF, which is the authority."""
        return _plain(api.LAW.search(query[:200], k=5))

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True,
                                          openWorldHint=True))
    def make_brief(key: str, ctx: Context, language: str = "en") -> dict:
        """Run Prohori's investigator agent on one company: it gathers the record, offices, ban list, AI priority and
        relevant law, and writes a one-page review brief where every fact cites a numbered source. Takes about 15
        seconds; saved briefs return at once. language = "en" or "bn" (Bangla). Limited per user per hour."""
        ip = (ctx.headers or {}).get("x-forwarded-for", "mcp").split(",")[0].strip() if ctx.headers else "mcp"
        brief = None
        for ev in api.INVESTIGATOR.stream(key, language, f"mcp:{ip}", api.data_date()):
            if ev["type"] == "brief":
                brief = ev
            elif ev["type"] == "error":
                return {"error": ev["message"]}
        return _plain({k: brief[k] for k in ("name", "text", "sources", "check", "made")} |
                      {"page": f"https://prohori.safeshare.co/#/brief/{key}", "notice": NOTICE})

    @mcp.tool(annotations=READ_ONLY)
    @_safe
    def company_awards_ocds(key: str, limit: int = 100) -> dict:
        """One company's contract awards in the Open Contracting Data Standard (OCDS 1.1) as a release package,
        newest first (max 500). Official award facts only; no risk scores."""
        return _plain(api.ocds_company(key, max(1, min(500, limit))))

    @mcp.tool(annotations=READ_ONLY)
    def compare_countries() -> dict:
        """The same rule-based checks (one firm dominating an office, no-competition buying, single-bid tenders,
        short bidding windows, concentration among top suppliers) run on Bangladesh and on other countries' open
        contracting data (Kenya, Nepal, India - Assam). Shows which checks each country's data allows."""
        return _plain(api.global_checks())

    return mcp


def http_app(mcp, allowed_hosts=("prohori.safeshare.co",)):
    """Stateless Streamable HTTP app at /mcp, with DNS-rebinding protection limited to Prohori's host names."""
    return mcp.streamable_http_app(
        streamable_http_path="/mcp", stateless_http=True, json_response=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[*allowed_hosts, "localhost:*", "127.0.0.1:*"],
            allowed_origins=[*(f"https://{h}" for h in allowed_hosts), "http://localhost:*", "http://127.0.0.1:*"]))


if __name__ == "__main__":
    import app.main as main
    main.MCP.run()          # stdio
