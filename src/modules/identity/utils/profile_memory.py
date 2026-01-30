import re
from typing import Optional
from unicodedata import category as unicode_category
from unicodedata import normalize
from unicodedata import combining


_NAME_PATTERNS = [
    r"\bmeu nome é\s+(?P<name>.+)",
    r"\beu me chamo\s+(?P<name>.+)",
    r"\bme chamo\s+(?P<name>.+)",
    r"\bpode me chamar de\s+(?P<name>.+)",
    r"\bpode chamar de\s+(?P<name>.+)",
    r"\beu sou o\s+(?P<name>.+)",
    r"\beu sou a\s+(?P<name>.+)",
    r"\bsou o\s+(?P<name>.+)",
    r"\bsou a\s+(?P<name>.+)",
    r"\bmy name is\s+(?P<name>.+)",
    r"\bi am\s+(?P<name>.+)",
    r"\bcall me\s+(?P<name>.+)",
]

_FORGET_PATTERNS = [
    r"\besquece\b.*\bmeu nome\b",
    r"\besqueça\b.*\bmeu nome\b",
    r"\bapaga\b.*\bmeu nome\b",
    r"\bapague\b.*\bmeu nome\b",
    r"\bremova\b.*\bmeu nome\b",
    r"\bdelete\b.*\bmy name\b",
    r"\bforget\b.*\bmy name\b",
]


def _strip_accents(text: str) -> str:
    decomposed = normalize("NFD", text)
    return "".join(ch for ch in decomposed if not combining(ch))


def _clean_candidate_name(raw: str) -> str:
    candidate = raw.strip()
    for sep in [",", ".", "!", "?", "\n", "\r", "\t", " - "]:
        if sep in candidate:
            candidate = candidate.split(sep, 1)[0].strip()
    for sep in [" e ", " and ", " eu ", " i "]:
        lowered = candidate.lower()
        idx = lowered.find(sep)
        if idx > 0:
            candidate = candidate[:idx].strip()
    candidate = re.sub(r"\s{2,}", " ", candidate)
    candidate = candidate.strip(" '\"")
    return candidate


def _looks_like_name(name: str) -> bool:
    if not name or len(name) < 2 or len(name) > 60:
        return False
    if any(ch.isdigit() for ch in name):
        return False
    for ch in name:
        if ch.isalpha() or ch in {" ", "-", "'", "’"}:
            continue
        if unicode_category(ch).startswith("P"):
            return False
        if unicode_category(ch).startswith("S"):
            return False
    words = [w for w in name.replace("-", " ").split() if w]
    if not words:
        return False
    if len(words) > 5:
        return False
    ascii_folded = _strip_accents(name).lower()
    if "http" in ascii_folded or "@" in name:
        return False
    return True


def extract_profile_name(text: str) -> Optional[str]:
    if not text or not text.strip():
        return None
    haystack = text.strip()
    for pattern in _NAME_PATTERNS:
        match = re.search(pattern, haystack, flags=re.IGNORECASE)
        if not match:
            continue
        raw_name = match.group("name")
        candidate = _clean_candidate_name(raw_name)
        if _looks_like_name(candidate):
            return candidate
    return None


def should_forget_profile(text: str) -> bool:
    if not text or not text.strip():
        return False
    haystack = text.strip()
    for pattern in _FORGET_PATTERNS:
        if re.search(pattern, haystack, flags=re.IGNORECASE):
            return True
    lowered = haystack.lower()
    return lowered.strip() in {"esquecer", "apagar memória", "apagar memoria", "/forget", "/esquecer"}
