"""Law search (retrieval-augmented generation) over Bangladesh's procurement law.

The index (app/law/law_index.json) is built by pipeline/build_law_index.py from the official BPPA PDFs:
Public Procurement Rules 2025, Public Procurement Act 2006 and its 2025 / 2026 amendments. Each part has
the machine-read Bangla text plus an English title, summary and keywords.

Search is hybrid:
  - keyword search (BM25) over the English summaries and the Bangla text, always available;
  - meaning search with Amazon Nova multimodal embeddings (law_vectors.npy), so an English question
    can find a Bangla rule even when no words match. If Bedrock is unreachable, keyword search alone is used.
The two rankings are merged with reciprocal rank fusion. Every result links to its page in the official PDF.
"""
import json
import math
import re
from collections import Counter
from pathlib import Path

import numpy as np

LAW_DIR = Path(__file__).resolve().parent / "law"
EMBED_MODEL = "amazon.nova-2-multimodal-embeddings-v1:0"
EMBED_DIM = 1024

WORD = re.compile(r"[a-z]{3,}|[ঀ-৿]{2,}")
STOP = {"the", "and", "for", "with", "that", "this", "from", "are", "may", "shall", "any", "its", "which",
        "will", "not", "has", "have", "been", "under", "such", "other", "into", "who", "per"}


def tokens(text: str) -> list[str]:
    return [w for w in WORD.findall(text.lower()) if w not in STOP]


def item_text(i: dict) -> str:
    """The text that represents one law part for meaning search."""
    return " | ".join([i.get("title_en", ""), i.get("summary_en", ""), ", ".join(i.get("keywords", [])),
                       i.get("title_bn", ""), i.get("text", "")[:1500]])


def embed_texts(texts, purpose="GENERIC_RETRIEVAL", client=None):
    """Nova multimodal embeddings, one call per text (the API embeds one item per call)."""
    out = []
    for t in texts:
        body = {"taskType": "SINGLE_EMBEDDING", "singleEmbeddingParams": {
            "embeddingPurpose": purpose, "embeddingDimension": EMBED_DIM,
            "text": {"truncationMode": "END", "value": t[:8000]}}}
        r = client.invoke_model(modelId=EMBED_MODEL, body=json.dumps(body))
        out.append(json.loads(r["body"].read())["embeddings"][0]["embedding"])
    return out


class LawIndex:
    def __init__(self, client_factory=None):
        p = LAW_DIR / "law_index.json"
        self.ok = p.exists()
        self.items, self.docs = [], {}
        self._client_factory = client_factory
        self.vectors = None
        if not self.ok:
            return
        data = json.loads(p.read_text(encoding="utf8"))
        self.docs, self.items = data["docs"], data["items"]
        # BM25: English summary words count double, so plain-English questions match well.
        self.tf = []
        for i in self.items:
            toks = tokens(" ".join([i.get("title_en", ""), i.get("summary_en", ""), " ".join(i.get("keywords", []))])) * 2
            toks += tokens(i.get("title_bn", "") + " " + i.get("text", ""))
            self.tf.append(Counter(toks))
        self.dl = [sum(c.values()) for c in self.tf]
        self.avgdl = sum(self.dl) / max(1, len(self.dl))
        df = Counter(w for c in self.tf for w in c)
        n = len(self.items)
        self.idf = {w: math.log(1 + (n - d + 0.5) / (d + 0.5)) for w, d in df.items()}
        vp = LAW_DIR / "law_vectors.npy"
        if vp.exists():
            v = np.load(vp)
            if len(v) == n:
                self.vectors = v / np.linalg.norm(v, axis=1, keepdims=True)

    def _bm25(self, q: str):
        qt = tokens(q)
        k1, b = 1.4, 0.75
        scores = np.zeros(len(self.items))
        for j, tf in enumerate(self.tf):
            s = 0.0
            for w in qt:
                f = tf.get(w)
                if f:
                    s += self.idf[w] * f * (k1 + 1) / (f + k1 * (1 - b + b * self.dl[j] / self.avgdl))
            scores[j] = s
        return scores

    def _semantic(self, q: str):
        if self.vectors is None or self._client_factory is None:
            return None
        try:
            v = np.asarray(embed_texts([q], "GENERIC_RETRIEVAL", self._client_factory())[0], dtype=np.float32)
        except Exception:
            return None
        return self.vectors @ (v / np.linalg.norm(v))

    def search(self, query: str, k: int = 4) -> dict:
        if not self.ok:
            return {"method": "unavailable", "results": []}
        bm = self._bm25(query)
        sem = self._semantic(query)
        # Reciprocal rank fusion of the two rankings (keyword ranking only if meaning search is unavailable).
        fused = np.zeros(len(self.items))
        for s in [bm] + ([sem] if sem is not None else []):
            for rank, j in enumerate(np.argsort(-s)[:50]):
                if s[j] > 0:
                    fused[j] += 1 / (60 + rank)
        order = [j for j in np.argsort(-fused) if fused[j] > 0]
        out = [self.result(self.items[j]) for j in order[:k]]
        return {"method": "keyword + meaning (Nova embeddings)" if sem is not None else "keyword", "results": out}

    def result(self, i: dict) -> dict:
        """One search result = one page of the official PDF. A rule / section number is given only when the
        index builder confirmed it (see pipeline/build_law_index.py); otherwise the page number is the reference."""
        d = self.docs[i["doc"]]
        many = "–" in i["number"]
        unit = ("Rules" if many else "Rule") if d["unit"] == "rule" else ("Sections" if many else "Section")
        unit_bn = "বিধি" if d["unit"] == "rule" else "ধারা"
        bn_num = i["number"].translate(str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯"))
        bn_page = str(i["page"]).translate(str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯"))
        return {"law": d["title_en"], "law_bn": d["title_bn"],
                "ref": f"{unit} {i['number']} (PDF page {i['page']})" if i["number"] else f"PDF page {i['page']}",
                "ref_bn": f"{unit_bn} {bn_num} (পিডিএফ পৃষ্ঠা {bn_page})" if i["number"] else f"পিডিএফ পৃষ্ঠা {bn_page}",
                "title_en": i.get("title_en", ""), "title_bn": i.get("title_bn", ""),
                "summary_en": i.get("summary_en", ""),
                "excerpt_bn": re.sub(r"\s+", " ", i.get("text", ""))[:600],
                "page": i["page"], "url": f"{d['url']}#page={i['page']}"}
