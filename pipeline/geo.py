"""Bangladesh districts -> divisions, with the spelling variants found in e-GP data."""
import re

DIVISIONS = {
    "Dhaka": ["Dhaka", "Gazipur", "Narayanganj", "Tangail", "Kishoreganj", "Manikganj", "Munshiganj",
              "Narsingdi", "Faridpur", "Gopalganj", "Madaripur", "Rajbari", "Shariatpur"],
    "Mymensingh": ["Mymensingh", "Jamalpur", "Netrokona", "Sherpur"],
    "Chattogram": ["Chattogram", "Cox's Bazar", "Cumilla", "Brahmanbaria", "Chandpur", "Noakhali", "Feni",
                   "Lakshmipur", "Rangamati", "Khagrachari", "Bandarban"],
    "Rajshahi": ["Rajshahi", "Bogura", "Pabna", "Sirajganj", "Naogaon", "Natore", "Joypurhat",
                 "Chapai Nawabganj"],
    "Khulna": ["Khulna", "Jashore", "Kushtia", "Bagerhat", "Satkhira", "Jhenaidah", "Magura", "Narail",
               "Chuadanga", "Meherpur"],
    "Barishal": ["Barishal", "Patuakhali", "Bhola", "Pirojpur", "Barguna", "Jhalokathi"],
    "Sylhet": ["Sylhet", "Moulvibazar", "Habiganj", "Sunamganj"],
    "Rangpur": ["Rangpur", "Dinajpur", "Kurigram", "Nilphamari", "Gaibandha", "Thakurgaon", "Lalmonirhat",
                "Panchagarh"],
}

# Old/alternative spellings -> canonical district name.
ALIASES = {
    "chittagong": "Chattogram", "comilla": "Cumilla", "barisal": "Barishal", "bogra": "Bogura",
    "jessore": "Jashore", "norshingdi": "Narsingdi", "narshingdi": "Narsingdi", "perojpur": "Pirojpur",
    "laksmipur": "Lakshmipur", "laxmipur": "Lakshmipur", "chapainawabganj": "Chapai Nawabganj",
    "nawabganj": "Chapai Nawabganj", "coxs bazar": "Cox's Bazar", "cox's bazar": "Cox's Bazar",
    "moulvi bazar": "Moulvibazar", "maulvibazar": "Moulvibazar", "jhalakati": "Jhalokathi",
    "jhalokati": "Jhalokathi", "netrakona": "Netrokona", "brahmanbaria": "Brahmanbaria",
    "khagrachhari": "Khagrachari", "chuadanga": "Chuadanga", "kishorganj": "Kishoreganj",
}

DISTRICT_TO_DIVISION = {d.lower(): div for div, ds in DIVISIONS.items() for d in ds}


def canonical_district(name: str | None) -> str | None:
    if not name:
        return None
    key = re.sub(r"\s+", " ", name.strip().strip(".").lower())
    if key in DISTRICT_TO_DIVISION:
        return next(d for ds in DIVISIONS.values() for d in ds if d.lower() == key)
    return ALIASES.get(key) or ALIASES.get(key.replace(" ", ""))


def division_of(district: str | None) -> str | None:
    d = canonical_district(district)
    return DISTRICT_TO_DIVISION.get(d.lower()) if d else None


_ALL_NAMES = sorted({d.lower() for d in DISTRICT_TO_DIVISION} | set(ALIASES), key=len, reverse=True)


def district_from_address(address: str | None) -> str | None:
    """e-GP addresses end with ',<upazila>,<district>.'; fall back to the last district name mentioned."""
    if not address:
        return None
    parts = [p.strip(" .") for p in address.split(",") if p.strip(" .")]
    for p in reversed(parts):
        d = canonical_district(p)
        if d:
            return d
    low = address.lower()
    hits = [(low.rfind(n), n) for n in _ALL_NAMES if n in low]
    return canonical_district(max(hits)[1]) if hits else None
