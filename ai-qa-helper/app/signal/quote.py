"""Verification that the model's quote really appears in the evidence."""

import re
import unicodedata

MIN_QUOTE_CHARS = 20
"""Minimum normalised length for a quote to count as evidence (avoids trivial matches like "yes")."""

_SINGLE = re.compile("[‘’‚‛]")
_DOUBLE = re.compile("[“”„‟]")
_DASH = re.compile("[‐-―−]")
_SPACE = re.compile(r"\s+")
_EDGES = re.compile(r"^[\"'.\s]+|[\"'.\s]+$")


def normalize_for_match(text: str) -> str:
    t = unicodedata.normalize("NFKC", text).lower()
    t = _SINGLE.sub("'", t)
    t = _DOUBLE.sub('"', t)
    t = _DASH.sub("-", t)
    t = t.replace("…", "...")
    return _SPACE.sub(" ", t).strip()


def is_quote_in_evidence(quote: str, evidence: str) -> bool:
    q = _EDGES.sub("", normalize_for_match(quote))
    if len(q) < MIN_QUOTE_CHARS:
        return False
    return q in normalize_for_match(evidence)
