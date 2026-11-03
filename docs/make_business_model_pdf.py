"""Build docs/Prohori_Business_Model.pdf — a short, plain-English business model for the team."""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

OUT = Path(__file__).with_name("Prohori_Business_Model.pdf")
LOGO = Path(__file__).resolve().parent.parent / "brand" / "png" / "prohori-icon-512.png"
FONTS = Path("C:/Windows/Fonts")
pdfmetrics.registerFont(TTFont("Body", str(FONTS / "calibri.ttf")))
pdfmetrics.registerFont(TTFont("Body-Bold", str(FONTS / "calibrib.ttf")))
pdfmetrics.registerFont(TTFont("Body-Italic", str(FONTS / "calibrii.ttf")))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body-Italic")

INK = colors.HexColor("#1F2933")
MUTED = colors.HexColor("#52606D")
BRAND = colors.HexColor("#0B6E4F")      # deep green
BRAND_LIGHT = colors.HexColor("#E3F1EC")
ACCENT = colors.HexColor("#C2410C")     # warm orange for warnings
GRID = colors.HexColor("#CBD2D9")

H1 = ParagraphStyle("H1", fontName="Body-Bold", fontSize=22, leading=27, textColor=BRAND, spaceAfter=4)
SUB = ParagraphStyle("Sub", fontName="Body", fontSize=12.5, leading=17, textColor=MUTED, spaceAfter=10)
H2 = ParagraphStyle("H2", fontName="Body-Bold", fontSize=15, leading=19, textColor=BRAND,
                    spaceBefore=9, spaceAfter=5)
BODY = ParagraphStyle("Body", fontName="Body", fontSize=11, leading=15.5, textColor=INK, spaceAfter=6)
SMALL = ParagraphStyle("Small", parent=BODY, fontSize=9, leading=12, textColor=MUTED)
CELL = ParagraphStyle("Cell", parent=BODY, fontSize=10, leading=13, spaceAfter=0)
CELL_B = ParagraphStyle("CellB", parent=CELL, fontName="Body-Bold")
HEAD = ParagraphStyle("Head", parent=CELL, fontName="Body-Bold", textColor=colors.white)
BOX = ParagraphStyle("Box", parent=BODY, fontSize=11.5, leading=16, spaceAfter=0)
QUOTE = ParagraphStyle("Quote", parent=BODY, fontName="Body-Italic", fontSize=12, leading=17,
                       alignment=TA_CENTER, textColor=INK, spaceAfter=0)


def p(text, style=BODY):
    return Paragraph(text, style)


def bullets(items):
    return [p(f"•&nbsp;&nbsp;{t}") for t in items]


def table(rows, widths, first_col_bold=True):
    data = [[p(c, HEAD) for c in rows[0]]]
    for r in rows[1:]:
        data.append([p(c, CELL_B if (i == 0 and first_col_bold) else CELL) for i, c in enumerate(r)])
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FA")]),
        ("GRID", (0, 0), (-1, -1), 0.5, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def callout(text, fill=BRAND_LIGHT, edge=BRAND, style=BOX):
    t = Table([[p(text, style)]], colWidths=[170 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fill),
        ("LINEBEFORE", (0, 0), (0, -1), 3, edge),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Body", 8.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(20 * mm, 12 * mm, "Prohori — Business Model · Team document · November 2026")
    canvas.drawRightString(190 * mm, 12 * mm, f"Page {doc.page}")
    canvas.restoreState()


story = []

# ---- Page 1: idea + why now ----
title_block = Table(
    [[Image(str(LOGO), width=20 * mm, height=20 * mm),
      [p("Prohori — How We Make Money", H1),
       p("Business model for the International AI Builders Congress 2026 · "
         "Idea to Unicorn → CivicSphere AI → Transparent Government", SUB)]]],
    colWidths=[24 * mm, 146 * mm])
title_block.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
]))

story += [
    title_block,
    callout("<b>Prohori</b> (\"watchman\") is an AI that reads every Bangladesh government contract on the "
            "public e-GP website and shows which ones look risky — and <b>why</b> — in simple Bangla. "
            "<b>The public uses it free. Businesses pay for deeper features.</b>"),
    Spacer(1, 8),
    p("1. The idea in 30 seconds", H2),
    *bullets([
        "The government buys roads, buildings, medicine and more through about <b>123,000 tenders a year</b>, "
        "worth about <b>Tk 1 lakh crore a year</b>.",
        "Every tender and contract is posted on the government's e-GP website by law. Our app pulls this "
        "data automatically every day — <b>the raw material is free</b>.",
        "Our AI turns about <b>900,000 raw contracts</b> into useful answers: risk warnings, hidden company "
        "networks, fair price ranges, and tender matches.",
        "Our value is not the data (anyone can see e-GP). Our value is the <b>analysis</b> — like Google: "
        "websites are public, but Google makes them useful.",
    ]),
    p("2. Why the timing is right", H2),
    table([
        ["Fact", "What it means for us"],
        ["New rules (PPR 2025) made e-GP <b>mandatory</b> for all government buying from Sept 2025",
         "All public procurement is now online — our data covers the whole market"],
        ["Average bidders per tender jumped from <b>2.2 to 8.4</b>",
         "Competition roughly 4x harder — contractors need help to win"],
        ["<b>143,374</b> companies registered on e-GP (Nov 2025), the biggest yearly jump ever",
         "A large, growing group of potential paying customers"],
        ["TIB found the <b>top 5% of contractors won 61%</b> of contract value",
         "Strong public interest in transparency — free users, media attention, trust"],
    ], [85 * mm, 85 * mm]),
]

# ---- Page 2: free vs paid + customers ----
story += [
    PageBreak(),
    p("3. The core model: free for the public, paid for business", H2),
    table([
        ["", "Free (public watchdog)", "Paid (business features)"],
        ["Who", "Citizens, journalists, students, NGOs", "Contractors, banks, government offices, donor projects"],
        ["What they get", "Risk patterns by area and office, Bangla Q&amp;A (\"Who builds roads in my upazila?\"), "
                          "officially banned companies",
         "Tender alerts, competitor and price intelligence, contractor risk reports, auditor dashboard, API"],
        ["Why it matters", "Builds <b>trust, fame and media coverage</b> — this is our marketing",
         "This is our <b>income</b>"],
    ], [28 * mm, 66 * mm, 76 * mm]),
    p("4. Who pays us — and why", H2),
    p("A company pays only when we <b>make them money, save them money, or protect them from losing money</b>."),
    table([
        ["Customer", "Their problem", "What Prohori gives them", "Price idea"],
        ["1. Contractors<br/>(143,000+)",
         "8 bidders per tender now. Hours wasted searching. Guessing the bid price.",
         "<b>Prohori Pro:</b> tenders that fit them, past winning-price ranges, who usually wins where",
         "Tk 1,500 / month"],
        ["2. Banks",
         "They give contractors loans and guarantees. A bad contractor = crores lost.",
         "Contractor risk report: past bans, linked companies, unfinished work",
         "Tk 5–15 lakh / bank / year, or per report"],
        ["3. Government &amp; auditors<br/>(BPPA, CAG, ACC)",
         "Can only check a tiny share of ~123,000 tenders a year.",
         "Ranked list: \"check these 200 risky contracts first\"",
         "Yearly licence"],
        ["4. Donor projects<br/>(World Bank, ADB, JICA)",
         "Must monitor how their loans are spent; pay consultants to do it by hand.",
         "Automatic integrity monitoring of their projects' contracts",
         "Project contracts (often USD 50k+)"],
        ["5. Grants",
         "Anti-corruption and open-data funders want tools like this.",
         "A working, proven product",
         "One-time grants"],
    ], [32 * mm, 44 * mm, 58 * mm, 36 * mm]),
    Spacer(1, 6),
    callout("<b>Simple version for judges:</b> Contractors pay because Prohori helps them <b>win more contracts</b>. "
            "Banks pay because it helps them <b>avoid bad loans</b>. Government and donors pay because it helps them "
            "<b>find wasted money faster</b>. The public uses it free, which builds trust."),
]

# ---- Page 3: numbers + costs ----
story += [
    PageBreak(),
    p("5. Example income (illustrative)", H2),
    p("These are <b>assumptions to show the shape of the business</b>, not tested sales. "
      "No customer has been asked yet."),
    table([
        ["Income source", "Year 1", "Year 2", "Year 3"],
        ["Contractors (Tk 1,500/month)", "300 users<br/>≈ Tk 54 lakh", "1,500 users<br/>≈ Tk 2.7 crore",
         "3,000 users (~2% of market)<br/>≈ Tk 5.4 crore"],
        ["Banks", "3 banks<br/>≈ Tk 24 lakh", "8 banks<br/>≈ Tk 64 lakh", "15 banks<br/>≈ Tk 1.2 crore"],
        ["Government / donor projects", "1 grant or pilot<br/>≈ Tk 30 lakh", "1 contract<br/>≈ Tk 60 lakh",
         "2–3 contracts<br/>≈ Tk 1.5 crore"],
        ["Other countries (Nepal, Bhutan…)", "—", "—", "1 pilot<br/>≈ Tk 1 crore"],
        ["<b>Total (approx.)</b>", "<b>≈ Tk 1.1 crore</b>", "<b>≈ Tk 4 crore</b>", "<b>≈ Tk 9 crore</b>"],
    ], [52 * mm, 36 * mm, 38 * mm, 44 * mm]),
    p("6. Our costs are low", H2),
    *bullets([
        "<b>Data:</b> free (published by the government).",
        "<b>Cloud + AI:</b> runs on AWS. The hackathon build costs about <b>USD 50–75</b>, covered by our AWS credits.",
        "<b>Running cost later:</b> a few hundred USD a month for servers and AI, growing slowly with users.",
        "<b>Team:</b> the system is mostly automatic, so a small team can run it. The biggest future cost is "
        "salaries for sales and support.",
    ]),
    p("Comparison: a UK company doing procurement intelligence (Tussell) charges about <b>£11,400 per licence "
      "per year</b> and was valued at <b>£5 million</b> after early funding in 2018. Similar companies exist in the "
      "US (GovSpend). The model works elsewhere; we found no one doing it for Bangladesh.", BODY),
    Spacer(1, 10),
    p("Sources: BPPA e-GP statistics (Nov 2025); BSS on bidders per tender (2.2 → 8.4); Transparency International "
      "Bangladesh e-procurement report (2025); UK G-Cloud listing and UKTech News on Tussell; World Bank ProACT; "
      "Open Contracting Partnership (Cardinal); OECD OPSI on Brazil's ALICE; TI Ukraine on DOZORRO. Income figures "
      "in section 5 are illustrative assumptions.", SMALL),
]

# ---- Page 4: growth, competition, risks ----
story += [
    PageBreak(),
    p("7. How we grow", H2),
    table([
        ["Stage", "Goal", "Money"],
        ["Now — hackathon", "Free public watchdog + risk model with proof (it flags banned companies "
                            "<b>before</b> the ban)", "AWS credits"],
        ["First 6 months", "Launch Prohori Pro for contractors", "First subscription income"],
        ["Year 1", "Contractor risk reports for banks", "Bigger, steadier income"],
        ["Year 2+", "Licences for government and donor projects", "Large contracts"],
        ["Year 3+", "Same product in Nepal, Bhutan and other e-GP countries", "Growth beyond Bangladesh"],
    ], [34 * mm, 96 * mm, 40 * mm]),
    p("8. Does anything like this already exist?", H2),
    table([
        ["What exists", "Why Prohori is different"],
        ["e-GP website itself", "Shows contracts one by one; no checking or warnings"],
        ["Dorpatra.com, data scrapers", "Copy raw tender data; no analysis"],
        ["TIB reports", "One-time PDF studies; Prohori is a live, searchable tool"],
        ["World Bank ProACT, Open Contracting \"Cardinal\"", "Global tools; Bangladesh not confirmed; no Bangla, "
                                                             "no owner networks"],
        ["Brazil's ALICE, Ukraine's DOZORRO", "Proven AI watchdogs — but only for their own countries"],
    ], [62 * mm, 108 * mm]),
    p("<b>Our moat (why others can't easily copy):</b> a cleaned 15-year contract history, the company–owner "
      "network, trained models with measured accuracy, and brand trust.", BODY),
    p("9. Risks — and our answers", H2),
    table([
        ["Risk", "Our answer"],
        ["Government limits access to e-GP data", "Read gently; later ask BPPA for an official data feed — partner, don't fight"],
        ["Small contractors pay little", "Cheap plans for them; bigger money from banks, government and donors"],
        ["Government sales are slow", "Start with contractors and banks, who decide faster"],
        ["Political or legal pressure", "Never say \"corrupt\" — only \"risk pattern, needs review\". A human always "
                                        "decides. Publicly name only companies the government already banned"],
        ["Others copy the idea", "Our 15-year cleaned data, owner network and trained models take time to rebuild"],
    ], [58 * mm, 112 * mm]),
    Spacer(1, 6),
    KeepTogether([callout("\"Prohori is free for citizens and paid for business. Contractors pay to win more, banks pay "
                          "to lose less, and government pays to find waste faster — all built on data the government "
                          "already publishes for free.\"", style=QUOTE)]),
]

doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                        topMargin=18 * mm, bottomMargin=20 * mm,
                        title="Prohori — Business Model", author="Prohori team")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(f"wrote {OUT}")
