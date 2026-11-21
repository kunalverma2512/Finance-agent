import re
import unicodedata

_NOISE = {"pos", "purchase", "debit", "card", "payment", "visa", "mastercard", "online", "www", "com",
          "the", "inc", "llc", "ltd", "txn", "ref", "ach", "pmt", "checkcard", "recurring", "dda"}
_CTRL = re.compile(r"[\x00-\x1f\x7f]")


def clean_text(value: str, max_len: int = 500) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = _CTRL.sub(" ", value)
    return re.sub(r"\s+", " ", value).strip()[:max_len]


def tokens(text: str) -> list[str]:
    words = re.sub(r"[^a-z&' ]", " ", text.lower()).split()
    return [w for w in words if len(w) > 1 and w not in _NOISE]


def normalize_merchant(description: str) -> str:
    toks = tokens(description)[:3]
    if toks:
        return " ".join(toks)[:255]
    return clean_text(description.lower(), 40)
