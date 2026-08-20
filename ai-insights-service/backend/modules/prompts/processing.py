"""Prompt Manager logic: read, validate and persist the prompts used by the service.

Each prompt record keeps two copies of the section text:

- `default_prompt` — the code-defined baseline, always overwritten from the registry on
  read so it can never drift from what ships in the image. Acts as the fallback.
- `user_prompt` — what editors saved through the Prompt Manager. This is the version
  actually used to generate overviews.

Records are stored one JSON per prompt ID in S3. A missing record is seeded from the
registry defaults on read, so no manual deploy step is needed to bootstrap a prompt.
"""

import re
from collections import Counter
from datetime import datetime, timezone

from utils.logger.logger_util import get_logger
from utils.s3.s3_util import get_prompt_json, save_prompt_json
from ai.prompts.registry import (
    PROMPT_SECTIONS,
    get_default_sections,
    get_prompt_definition,
    get_variables,
    known_prompt_ids,
)

logger = get_logger()

# Matches every {placeholder} in the prompt text. Deliberately excludes '{' and '}' so
# the JSON object literal in the output-format section is never treated as a variable.
_PLACEHOLDER_PATTERN = re.compile(r"\{([a-zA-Z0-9_]+)\}")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sections_from(raw: dict | None, defaults: dict[str, str]) -> dict[str, str]:
    """Read section text, falling back to the default for anything missing or blank."""
    raw = raw or {}
    sections = {}
    for section in PROMPT_SECTIONS:
        value = raw.get(section)
        if not isinstance(value, str) or not value.strip():
            value = defaults[section]
        sections[section] = value
    return sections


def _count_placeholders(sections: dict[str, str]) -> Counter:
    """
    Count every {placeholder} across all sections combined.

    Counting across the whole prompt (rather than per section) is what lets a variable be
    moved between sections while still catching it being used twice.
    """
    counts = Counter()
    for text in sections.values():
        counts.update(_PLACEHOLDER_PATTERN.findall(text))
    return counts


def _find_placeholders(sections: dict[str, str]) -> set[str]:
    """Collect every {placeholder} used across all sections."""
    return set(_count_placeholders(sections))


def validate_sections(prompt_id: str, sections: dict[str, str]) -> None:
    """
    Check the submitted sections before they are persisted.

    Variables are looked for across ALL sections combined, so an editor is free to move
    a placeholder from `context` into `user_instructions` if that reads better.

    Raises:
        ValueError: If a required variable is missing or an unknown one is present.
    """
    variables = get_variables(prompt_id)
    known_names = {variable.name for variable in variables}
    required_names = {variable.name for variable in variables if variable.required}

    counts = _count_placeholders(sections)
    used = set(counts)

    missing = sorted(required_names - used)
    unknown = sorted(used - known_names)
    # Only known variables are worth flagging as duplicated — an unknown one repeated is
    # already reported as unknown, and saying both would just be noise.
    duplicated = sorted(name for name, count in counts.items() if count > 1 and name in known_names)

    # Reported together: a missing variable alongside an unknown one is almost always a
    # typo, and seeing only half of that pair hides the actual mistake.
    problems = []
    if missing:
        problems.append(
            "missing required context variables: "
            + ", ".join("{" + name + "}" for name in missing)
            + " (without them that context is silently dropped from the prompt)"
        )
    if unknown:
        problems.append(
            "unknown variables: "
            + ", ".join("{" + name + "}" for name in unknown)
            + " (these would be sent to the model literally)"
        )
    if duplicated:
        problems.append(
            "variables used more than once: "
            + ", ".join(
                "{" + name + "} appears " + str(counts[name]) + " times" for name in duplicated
            )
            + " (each variable must appear exactly once — repeating one injects the same "
            "context again and wastes tokens)"
        )

    if problems:
        raise ValueError(
            "Invalid context variables — "
            + "; ".join(problems)
            + ". Allowed variables: "
            + ", ".join("{" + name + "}" for name in sorted(known_names))
        )


def render_sections(sections: dict[str, str], values: dict[str, str]) -> str:
    """
    Assemble the four sections into the final prompt, substituting context variables.

    Uses str.replace() rather than str.format(): the expected-output-format section
    contains a JSON object literal full of braces, which str.format() would choke on.
    """
    ordered_text = "\n\n".join(sections[section] for section in PROMPT_SECTIONS)

    for name, value in values.items():
        ordered_text = ordered_text.replace("{" + name + "}", value)

    return ordered_text


def _build_record(
    prompt_id: str,
    stored: dict | None,
) -> dict:
    """Normalize a stored record (or a missing one) into the API shape."""
    definition = get_prompt_definition(prompt_id)
    defaults = get_default_sections(prompt_id)

    # Defaults always come from code so a stale S3 copy can never shadow them.
    user_prompt = _sections_from((stored or {}).get("user_prompt"), defaults)

    return {
        "id": prompt_id,
        "name": definition["name"],
        "description": definition["description"],
        "sections": list(PROMPT_SECTIONS),
        "variables": [variable.to_dict() for variable in get_variables(prompt_id)],
        "default_prompt": defaults,
        "user_prompt": user_prompt,
        "is_modified": user_prompt != defaults,
        "created_at": (stored or {}).get("created_at"),
        "updated_at": (stored or {}).get("updated_at"),
        "updated_by": (stored or {}).get("updated_by"),
    }


def get_prompt(prompt_id: str) -> dict:
    """
    Load a single prompt record, seeded from code defaults when nothing is stored yet.

    Raises:
        ValueError: If the prompt ID is not registered.
    """
    get_prompt_definition(prompt_id)  # validates the ID

    try:
        stored = get_prompt_json(prompt_id)
    except Exception as error:
        # Never fail the Prompt Manager because storage is unavailable — show the defaults.
        logger.error(f"Failed to load stored prompt '{prompt_id}': {str(error)}")
        stored = None

    if stored is None:
        logger.info(f"🌱 No stored prompt for '{prompt_id}' — returning code defaults")

    return _build_record(prompt_id, stored)


def get_all_prompts() -> list[dict]:
    """Every registered prompt, for STAR to filter by ID in the Prompt Manager."""
    prompt_ids = known_prompt_ids()
    logger.info(f"📋 Loading {len(prompt_ids)} registered prompt(s): {prompt_ids}")
    return [get_prompt(prompt_id) for prompt_id in prompt_ids]


def update_prompt(
    prompt_id: str,
    sections: dict[str, str],
    updated_by: str | None = None,
) -> dict:
    """
    Overwrite the user version of a prompt with the sections submitted by the editor.

    Args:
        prompt_id: Registered prompt ID (e.g. 'project-overview')
        sections: All four sections, replacing the stored user version entirely
        updated_by: Optional user identifier recorded for auditing

    Returns:
        The updated prompt record

    Raises:
        ValueError: If the prompt ID is unknown, a section is missing or blank, or the
            template dropped a required context variable
    """
    get_prompt_definition(prompt_id)  # validates the ID

    blank = [
        section
        for section in PROMPT_SECTIONS
        if not isinstance(sections.get(section), str) or not sections[section].strip()
    ]
    if blank:
        raise ValueError(f"These prompt sections cannot be empty: {', '.join(blank)}")

    clean_sections = {section: sections[section] for section in PROMPT_SECTIONS}
    validate_sections(prompt_id, clean_sections)

    try:
        stored = get_prompt_json(prompt_id)
    except Exception as error:
        logger.error(f"Failed to load stored prompt '{prompt_id}' before update: {str(error)}")
        stored = None

    timestamp = _now_iso()
    record = {
        "id": prompt_id,
        "user_prompt": clean_sections,
        "created_at": (stored or {}).get("created_at") or timestamp,
        "updated_at": timestamp,
        "updated_by": updated_by,
    }

    save_prompt_json(prompt_id, record)
    logger.info(f"✅ Prompt '{prompt_id}' updated (by={updated_by or 'N/A'})")

    return _build_record(prompt_id, record)


def get_active_sections(prompt_id: str) -> dict[str, str]:
    """
    The sections to actually use for generation: the user version, or code defaults.

    Never raises for storage problems — generation must keep working even if the
    Prompt Manager backend is unavailable.
    """
    try:
        return get_prompt(prompt_id)["user_prompt"]
    except Exception as error:
        logger.error(
            f"Falling back to default prompt sections for '{prompt_id}': {str(error)}"
        )
        return get_default_sections(prompt_id)
