"""Company-name helpers shared by the pipeline scripts."""
import re

LIGHT_NOISE = re.compile(r"\b(m/?s|messrs|the|ltd|limited|pvt|private)\b")


def strict_key(name: str) -> str:
    """Identity key: case, punctuation, M/S, Ltd and Pvt removed; all real words kept."""
    s = name.lower().replace("&", " and ")
    s = LIGHT_NOISE.sub(" ", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def clean_name(name: str) -> str:
    """Readable name for display."""
    s = re.sub(r"^\s*m\s*/?\s*s\.?\s+", "", name.strip(), flags=re.I)
    return re.sub(r"\s+", " ", s).strip(" .,")


def is_joint_venture(name: str) -> bool:
    return bool(re.search(r"\bj\.?\s?v\.?\b|joint venture|\bjv\b", name, re.I))
