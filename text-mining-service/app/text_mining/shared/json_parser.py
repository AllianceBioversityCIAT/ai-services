import re
import json


def extract_json_from_markdown(text):
    """Extract JSON from markdown code blocks if present."""
    json_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
    match = re.search(json_pattern, text, re.DOTALL)

    if match:
        return match.group(1).strip()

    return text.strip()


def _extract_balanced_json(text: str, start: int) -> str | None:
    """Return the first complete {...} object starting at start, respecting strings."""
    depth = 0
    in_string = False
    escape = False

    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    return None


def extract_json_object(text: str) -> str:
    """
    Extract a JSON object from model output.

    Handles prose before/after JSON and fenced ```json blocks.
    """
    if not text:
        return ""

    stripped = extract_json_from_markdown(text)
    if is_valid_json(stripped):
        return stripped

    for anchor in ('{"results"', '{\n  "results"', '{\r\n  "results"'):
        anchor_index = stripped.find(anchor)
        if anchor_index == -1:
            continue
        candidate = _extract_balanced_json(stripped, anchor_index)
        if candidate and is_valid_json(candidate):
            return candidate

    first_brace = stripped.find("{")
    if first_brace != -1:
        candidate = _extract_balanced_json(stripped, first_brace)
        if candidate and is_valid_json(candidate):
            return candidate

    return stripped.strip()


def is_valid_json(text):
    """Check if the text is a valid JSON string."""
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False