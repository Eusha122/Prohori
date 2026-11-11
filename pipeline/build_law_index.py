"""Build Prohori's law search index from the official procurement law PDFs published by BPPA.

The Bangla gazette PDFs use old font encodings, so their text cannot be copied out. Each page is read
as an image by Amazon Nova 2 Lite (machine reading), split into rules / sections, and each part gets a
short English title and summary written by Nova. Search results always link to the page of the official
PDF, because machine reading can contain small spelling mistakes.

Steps (each one resumes where it stopped):
    python pipeline/build_law_index.py download
    python pipeline/build_law_index.py ocr        # ~1 minute per page, run in parallel
    python pipeline/build_law_index.py chunk      # split pages into rules / sections
    python pipeline/build_law_index.py summarize  # English title + summary for each part
    python pipeline/build_law_index.py embed      # vectors for meaning-based search (optional)
    python pipeline/build_law_index.py all

Output: app/law/law_index.json (and law_vectors.npy if embeddings are available), used by app/law.py.
"""
import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "law" / "raw"
OCR = ROOT / "data" / "law" / "ocr"
WORK = ROOT / "data" / "law"
OUT = ROOT / "app" / "law"

BPPA = "https://bppa.gov.bd/upload/policyandprocedure/"
DOCS = [
    {"id": "ppr2025", "file": "2025-09-29-20-12-59-PPR2025.pdf", "unit": "rule",
     "title_en": "Public Procurement Rules 2025", "title_bn": "সরকারি ক্রয় বিধিমালা, ২০২৫"},
    {"id": "ppa2006", "file": "2017-07-31-16-00-37-Public-Procurement-Act-2006-Bangla.pdf", "unit": "section",
     "title_en": "Public Procurement Act 2006", "title_bn": "সরকারি ক্রয় আইন, ২০০৬"},
    {"id": "ord2025", "file": "2025-05-08-17-07-37-Ordinance-No-16-of-2025.pdf", "unit": "section",
     "title_en": "Public Procurement (Amendment) Ordinance 2025", "title_bn": "সরকারি ক্রয় (সংশোধন) অধ্যাদেশ, ২০২৫"},
    {"id": "amd2026", "file": "2026-04-30-11-41-39-PP(Amendment)-Act-2026.pdf", "unit": "section",
     "title_en": "Public Procurement (Amendment) Act 2026", "title_bn": "সরকারি ক্রয় (সংশোধন) আইন, ২০২৬"},
]

MODEL = "us.amazon.nova-2-lite-v1:0"
EMBED_MODEL = "amazon.nova-2-multimodal-embeddings-v1:0"
REGION = "us-east-1"
WORKERS = 10

OCR_PROMPT = ("This is a page of the Bangladesh Gazette ({title}), in Bangla. Transcribe ALL the text on the page "
              "exactly, in Unicode Bangla, keeping rule / section numbers, sub-rule numbers and the line breaks "
              "between paragraphs. Do not translate, summarise or add anything. Output only the transcription.")

SUMMARY_PROMPT = """Below is one page of a Bangladesh procurement law ({title}), machine-read from the official Bangla gazette. It may contain spelling mistakes, and digits may be misread.
{rules}
Return ONLY a JSON object with these keys:
"title_en": a short English title for what this page covers (max 12 words);
"title_bn": the main Bangla heading on the page if there is one, else a short Bangla title;
"summary_en": 2 to 3 plain English sentences on what the text on this page requires or allows. Do NOT include any amounts, numbers of days, percentages or rule numbers (machine-read digits may be wrong); say "a set amount" or "a set time" instead. Do not add anything that is not in the text;
"keywords": 5 to 10 English keywords (for example "debarment", "direct procurement", "performance security").

TEXT:
<<<
{text}
>>>"""

BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def _client():
    import boto3
    from botocore.config import Config
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    return boto3.client("bedrock-runtime", region_name=REGION,
                        config=Config(read_timeout=300, retries={"max_attempts": 4, "mode": "adaptive"}))


def download():
    RAW.mkdir(parents=True, exist_ok=True)
    for d in DOCS:
        p = RAW / d["file"]
        if p.exists() and p.stat().st_size > 10_000:
            continue
        req = urllib.request.Request(BPPA + urllib.request.quote(d["file"]), headers={"User-Agent": "Mozilla/5.0"})
        p.write_bytes(urllib.request.urlopen(req, timeout=300).read())
        print("downloaded", d["file"])


def ocr():
    import pymupdf
    client = _client()
    jobs = []
    for d in DOCS:
        doc = pymupdf.open(RAW / d["file"])
        (OCR / d["id"]).mkdir(parents=True, exist_ok=True)
        for i in range(len(doc)):
            out = OCR / d["id"] / f"{i + 1:04d}.txt"
            if not out.exists():
                jobs.append((d, i, out))
    print(f"{len(jobs)} pages to read")

    def read(job):
        d, i, out = job
        png = pymupdf.open(RAW / d["file"])[i].get_pixmap(dpi=170).tobytes("png")
        r = client.converse(modelId=MODEL, messages=[{"role": "user", "content": [
            {"image": {"format": "png", "source": {"bytes": png}}},
            {"text": OCR_PROMPT.format(title=d["title_en"])}]}],
            inferenceConfig={"maxTokens": 7000, "temperature": 0})
        out.write_text(r["output"]["message"]["content"][0]["text"], encoding="utf8")
        return out

    done, t0 = 0, time.time()
    with ThreadPoolExecutor(WORKERS) as ex:
        for f in as_completed([ex.submit(read, j) for j in jobs]):
            try:
                f.result()
                done += 1
            except Exception as e:  # the page is retried on the next run
                print("failed:", e)
            if done % 10 == 0:
                print(f"{done}/{len(jobs)} pages, {time.time() - t0:.0f}s", flush=True)


# ---------- Splitting into pages, with rule / section numbers we can trust ----------
# Machine reading of Bangla digits is unreliable (it often reads ৪ as ৮, or the danda । as ১). So:
#  1. every line that looks like a rule heading ("৬৪। Title—(১) ...") becomes a candidate, with all the
#     numbers its digits could be (৪/৮, ১/৯, ৩/৬, ৫/৬ mix-ups, a danda read as ১);
#  2. the longest chain of candidates whose numbers go up in order (1, 2, 3 ...) is kept: those numbers are
#     confirmed by their neighbours;
#  3. each PAGE is one search unit. A page is labelled with a rule number only when a confirmed heading starts
#     on it or the page continues a confirmed rule with no unreadable heading in between; otherwise it is
#     labelled by its page number only. Every result links to the official PDF page.
HEAD = re.compile(r"^[\s*#]*([০-৯]{1,4})\s*([।৷|:১]|\s)\s*(?![০-৯(])(\S[^\n]{2,160})", re.M)
PAGE_HEADER = re.compile(r"^.*বাংলাদেশ গেজেট.*$\n?(^\s*[০-৯]{3,5}\s*$\n?)?", re.M)
CONF = {"4": "48", "8": "84", "1": "19", "9": "91", "3": "36", "6": "63", "5": "56"}


def _variants(s):
    import itertools
    s = s.translate(BN_DIGITS)
    bases = {s} | ({s[:-1]} if len(s) > 1 and s.endswith("1") else set())
    return {int("".join(c)) for b in bases for c in itertools.product(*[CONF.get(ch, ch) for ch in b])}


def _candidates(doc_id):
    cands = []
    for p in sorted((OCR / doc_id).glob("*.txt")):
        text = p.read_text(encoding="utf8")
        for m in HEAD.finditer(text):
            line = m.group(3)
            if not re.search(r"[—–]|-\s*\(|।\s*$", line[:170]) or re.match(r"(উদাহরণ|তবে|বিধি|ধারা)", line):
                continue
            cands.append({"opts": _variants(m.group(1)), "page": int(p.stem), "pos": m.start()})
    return cands


def _chain(cands, maxgap=12):
    """Longest, tightest increasing chain of heading numbers. Returns {candidate index: number}."""
    best = []
    for i, c in enumerate(cands):
        row = {}
        for v in c["opts"]:
            if not 1 <= v <= 400:
                continue
            sc = (10 - 2 * (v - 1) if v <= 5 else -100, None, None)
            for j in range(max(0, i - 40), i):
                for pv, (ps, _, _) in best[j].items():
                    if 1 <= v - pv <= maxgap and ps + 10 - 3 * (v - pv - 1) > sc[0]:
                        sc = (ps + 10 - 3 * (v - pv - 1), j, pv)
            row[v] = sc
        best.append(row)
    ends = [(s[0], i, v) for i, r in enumerate(best) for v, s in r.items()]
    if not ends:
        return {}
    _, i, v = max(ends)
    out = {}
    while i is not None:
        out[i] = v
        _, i, v = best[i][v]
    return out


def chunk():
    out = []
    for d in DOCS:
        cands = _candidates(d["id"])
        conf = _chain(cands)
        by_page = {}
        for i, c in enumerate(cands):
            by_page.setdefault(c["page"], []).append(conf.get(i))     # None = heading with unreadable number
        current = None                       # confirmed rule that is still running
        for p in sorted((OCR / d["id"]).glob("*.txt")):
            page = int(p.stem)
            heads = by_page.get(page, [])
            starts = [n for n in heads if n is not None]
            # The rule running from the previous page covers the top of this page; new rules start below it.
            numbers = ([current] if current else []) + starts
            if heads:
                current = heads[-1]          # None if the last heading on the page is unreadable
            text = PAGE_HEADER.sub("", p.read_text(encoding="utf8"))
            text = re.sub(r"^```\w*\s*$", "", text, flags=re.M)          # code fences the model sometimes adds
            text = re.sub(r"\n{3,}", "\n\n", text).strip()
            if len(text) < 40:
                continue
            numbers = sorted({n for n in numbers if n})
            out.append({"id": f"{d['id']}-p{page}", "doc": d["id"], "page": page, "numbers": numbers,
                        "number": (str(numbers[0]) if len(numbers) == 1 else
                                   f"{numbers[0]}–{numbers[-1]}" if numbers else ""), "text": text[:6000]})
        print(f"{d['id']}: {len(cands)} headings found, {len(conf)} numbers confirmed")
    (WORK / "chunks.json").write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf8")
    print(f"{len(out)} pages, {sum(1 for x in out if x['number'])} with a confirmed rule / section number")


def summarize():
    client = _client()
    chunks = json.loads((WORK / "chunks.json").read_text(encoding="utf8"))
    cache_p = WORK / "summaries.json"
    cache = json.loads(cache_p.read_text(encoding="utf8")) if cache_p.exists() else {}
    titles = {d["id"]: d["title_en"] for d in DOCS}
    todo = [c for c in chunks if c["id"] not in cache]
    print(f"{len(todo)} parts to summarize")

    def one(c):
        rules = (f"Rule / section numbers on this page (confirmed): {c['number']}." if c["number"] else "")
        r = client.converse(modelId=MODEL, messages=[{"role": "user", "content": [{"text": SUMMARY_PROMPT.format(
            title=titles[c["doc"]], rules=rules, text=c["text"][:5000])}]}],
            inferenceConfig={"maxTokens": 600, "temperature": 0})
        raw = r["output"]["message"]["content"][0]["text"]
        m = re.search(r"\{.*\}", raw, re.S)
        return c["id"], json.loads(m.group(0))

    with ThreadPoolExecutor(WORKERS) as ex:
        for i, f in enumerate(as_completed([ex.submit(one, c) for c in todo])):
            try:
                k, v = f.result()
                cache[k] = v
            except Exception as e:
                print("failed:", e)
            if i % 25 == 0:
                cache_p.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf8")
                print(i, "done", flush=True)
    cache_p.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf8")
    write_index(chunks, cache)


def write_index(chunks=None, cache=None):
    chunks = chunks or json.loads((WORK / "chunks.json").read_text(encoding="utf8"))
    cache = cache or json.loads((WORK / "summaries.json").read_text(encoding="utf8"))
    docs = {d["id"]: {**d, "url": BPPA + d["file"]} for d in DOCS}
    items = []
    for c in chunks:
        s = cache.get(c["id"], {})
        items.append({**c, "title_en": s.get("title_en", ""), "title_bn": s.get("title_bn", ""),
                      "summary_en": s.get("summary_en", ""), "keywords": s.get("keywords", [])})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "law_index.json").write_text(json.dumps({"docs": docs, "items": items}, ensure_ascii=False),
                                        encoding="utf8")
    print(f"wrote {OUT / 'law_index.json'}: {len(items)} parts, {sum(1 for i in items if i['summary_en'])} summarized")


def embed():
    """Vectors for meaning-based search (English question -> Bangla law). Skipped if the model is unavailable."""
    import numpy as np
    sys.path.insert(0, str(ROOT))
    from app.law import embed_texts, item_text
    idx = json.loads((OUT / "law_index.json").read_text(encoding="utf8"))
    vecs = embed_texts([item_text(i) for i in idx["items"]], purpose="GENERIC_INDEX", client=_client())
    np.save(OUT / "law_vectors.npy", np.asarray(vecs, dtype=np.float32))
    print("saved", len(vecs), "vectors")


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    steps = {"download": [download], "ocr": [ocr], "chunk": [chunk], "summarize": [summarize],
             "index": [write_index], "embed": [embed], "all": [download, ocr, chunk, summarize, embed]}
    for fn in steps[step]:
        fn()
