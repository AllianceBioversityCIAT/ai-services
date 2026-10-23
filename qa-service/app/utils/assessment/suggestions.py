"""
Validation for the replacement title and description the model proposes.

The Reporting Tool discards a malformed suggestion on its side, but a suggestion
is offered to the user as text they can apply with one click, so it is checked
here before it is ever sent. A rejected suggestion is dropped on its own and
never affects the verdict.
"""

import re
from typing import Optional

MAX_TITLE_WORDS = 30
MAX_DESCRIPTION_WORDS = 300
MIN_WORDS = 3

# Markdown emphasis and headings, HTML tags, and wrapping quotes - the contract
# asks for plain text the form can take verbatim.
_MARKUP = re.compile(r"<[^>]+>|\*\*|__|^#{1,6}\s|`")
_WRAPPING_QUOTES = re.compile(r'^["“‘\']+|["”’\']+$')


def _clean(text: Optional[str], one_line: bool) -> Optional[str]:
    if not isinstance(text, str):
        return None
    text = _WRAPPING_QUOTES.sub("", text.strip())
    if one_line:
        text = " ".join(text.split())
    else:
        # Keep paragraph breaks, collapse everything else.
        text = "\n".join(" ".join(p.split()) for p in text.split("\n") if p.strip())
    return text or None


def _acceptable(text: Optional[str], original: Optional[str], max_words: int) -> bool:
    if not text:
        return False
    if _MARKUP.search(text):
        return False
    words = len(text.split())
    if words < MIN_WORDS or words > max_words:
        return False
    # A suggestion identical to what the user already wrote is not a suggestion.
    norm = lambda s: " ".join((s or "").lower().split())
    return norm(text) != norm(original)


def validate(raw: dict, original_title: Optional[str],
             original_description: Optional[str]) -> Optional[dict]:
    """Return the usable suggestions, or None when neither survives."""
    if not isinstance(raw, dict):
        return None

    title = _clean(raw.get("title"), one_line=True)
    if not _acceptable(title, original_title, MAX_TITLE_WORDS):
        title = None

    description = _clean(raw.get("description"), one_line=False)
    if not _acceptable(description, original_description, MAX_DESCRIPTION_WORDS):
        description = None

    if title is None and description is None:
        return None
    return {"title": title, "description": description}
