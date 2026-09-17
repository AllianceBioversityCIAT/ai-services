"""
Forced-tool schemas for the assessment calls.

The criterion ids are baked into the schema as an `enum`, so the model cannot
report a finding that is not in the catalog. That is what keeps the review from
drifting: the set of possible issues is closed and shrinks as the user fixes
them, instead of the model finding something new to say on every re-run (AC5).
"""

from typing import List

from app.utils.assessment.criteria_catalog import Criterion


def _finding_item(criteria: List[Criterion]) -> dict:
    return {
        "type": "object",
        "properties": {
            "criterion_id": {
                "type": "string",
                "enum": [c.id for c in criteria],
                "description": "Must be one of the listed criteria. Do not invent ids.",
            },
            "outcome": {
                "type": "string",
                "enum": ["passed", "flagged"],
                "description": (
                    "'flagged' only when the criterion's flag condition is met. "
                    "When in doubt, use 'passed' - a false flag costs the user a "
                    "correction they did not need to make."
                ),
            },
            "comment": {
                "type": "string",
                "description": (
                    "One or two sentences in plain language for a reporting user, "
                    "not a QA specialist. When flagged, say what is missing or weak "
                    "and what would fix it. When passed, say briefly what the result "
                    "does well. Never mention criterion ids, scores, or internal terms."
                ),
            },
        },
        "required": ["criterion_id", "outcome", "comment"],
        "additionalProperties": False,
    }


def metadata_tool(criteria: List[Criterion]) -> dict:
    return {
        "name": "report_metadata_assessment",
        "description": "Report one finding for every criterion you were given. No more, no fewer.",
        "input_schema": {
            "type": "object",
            "properties": {"findings": {"type": "array", "items": _finding_item(criteria)}},
            "required": ["findings"],
            "additionalProperties": False,
        },
    }


def evidence_tool(criteria: List[Criterion], evidence_count: int) -> dict:
    return {
        "name": "report_evidence_assessment",
        "description": (
            "Report one finding for every criterion you were given, plus one verdict "
            "per evidence item."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "findings": {"type": "array", "items": _finding_item(criteria)},
                "evidence": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "index": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": max(0, evidence_count - 1),
                                "description": "Position of the evidence item as given to you.",
                            },
                            "verdict": {
                                "type": "string",
                                "enum": ["green", "amber", "red"],
                                "description": (
                                    "green: the item is genuine and clearly supports the "
                                    "result. amber: it is related but support is partial or "
                                    "indirect. red: it does not support the result, or is not "
                                    "what it claims to be."
                                ),
                            },
                            "reason": {
                                "type": "string",
                                "description": (
                                    "One sentence in plain language explaining the verdict, "
                                    "grounded in what the document actually says."
                                ),
                            },
                        },
                        "required": ["index", "verdict", "reason"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["findings", "evidence"],
            "additionalProperties": False,
        },
    }
