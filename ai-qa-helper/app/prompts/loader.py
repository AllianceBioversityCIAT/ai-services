"""Loads prompts by ``promptVersion`` from ``prompts/manifest.json``.

A promptVersion is immutable: every file it uses is pinned by sha256 in the manifest and checked on
load, so a stored suggestion always maps to the exact text that produced it. Changing a prompt means
adding a new version, never editing a released one.
"""

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from app.llm.output_schema import OUTPUT_MODELS, SuggestionOutput

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
"""Repository root ``prompts/``; the Lambda zip ships it next to ``app/``."""

Family = Literal["v1", "v2"]


class UnknownPromptVersion(Exception):
    """The job names a promptVersion that this worker build does not ship (configuration error)."""


class PromptIntegrityError(Exception):
    """A prompt file does not match the sha256 pinned in the manifest."""


@dataclass(frozen=True)
class PromptSpec:
    prompt_version: str
    family: Family
    field_key: str
    output_model: type[SuggestionOutput]
    text: str
    """v1: the previous helper's prompt, verbatim. v2: the rendered system prompt."""
    label: str


def get_prompt(prompt_version: str, field_key: str, prompts_dir: Path = PROMPTS_DIR) -> PromptSpec | None:
    """Returns None when the version has no criteria for the field (``no_criteria_for_field``)."""
    version = _manifest(prompts_dir)["versions"].get(prompt_version)
    if version is None:
        raise UnknownPromptVersion(prompt_version)
    entry = version["fields"].get(field_key)
    if entry is None:
        return None
    family: Family = version["family"]
    text = _read(prompts_dir, entry)
    if family == "v2":
        text = _render_v2(_read(prompts_dir, version["system"]), entry, text)
    return PromptSpec(
        prompt_version=prompt_version,
        family=family,
        field_key=field_key,
        output_model=OUTPUT_MODELS[entry["output"]],
        text=text,
        label=entry["label"],
    )


def prompt_versions(prompts_dir: Path = PROMPTS_DIR) -> list[str]:
    return sorted(_manifest(prompts_dir)["versions"])


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _render_v2(frame: str, entry: dict[str, str], criteria: str) -> str:
    for key, value in (
        ("{{FIELD_LABEL}}", entry["label"]),
        ("{{SCALE}}", entry["scale"]),
        ("{{COMPONENT_RULE}}", entry["component"]),
        ("{{EXPLANATION_RULE}}", entry["explanation"]),
        ("{{CRITERIA}}", criteria.strip()),
    ):
        frame = frame.replace(key, value)
    return frame


def _read(prompts_dir: Path, entry: dict[str, str]) -> str:
    path = prompts_dir / entry["file"]
    if file_sha256(path) != entry["sha256"]:
        raise PromptIntegrityError(entry["file"])
    return path.read_bytes().decode("utf-8")


@lru_cache(maxsize=4)
def _manifest(prompts_dir: Path) -> dict:
    return json.loads((prompts_dir / "manifest.json").read_text(encoding="utf-8"))
