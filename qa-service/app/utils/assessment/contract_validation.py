"""
Strict validation of the incoming payload against contract v0.2.

The type_specific fields are keyed by their visible form label, so the service
depends on those labels arriving exactly as agreed. When one is missing or spelled
differently the request is rejected with a specific message naming the label,
rather than silently evaluating fewer criteria than it should.
"""

from typing import List

from app.utils.assessment.vocabularies import (
    TYPE_SPECIFIC_LABELS,
    IMPACT_AREAS,
    SUBCOMPONENTS,
    EVIDENCE_TAGS,
    DELIVERY_METHODS,
    TRAINING_LENGTHS,
)


class ContractError(Exception):
    def __init__(self, problems: List[dict]):
        self.problems = problems
        super().__init__(f"{len(problems)} contract problem(s)")


def _norm(label: str) -> str:
    return " ".join(label.strip().lower().replace("(", " ").replace(")", " ").split())


def validate(request) -> List[dict]:
    """Return a list of contract problems. Empty list means the payload is clean."""
    problems = []
    result_type = (request.result.type or "").strip().lower()

    expected = TYPE_SPECIFIC_LABELS.get(result_type)
    if expected is None:
        problems.append({
            "code": "UNKNOWN_RESULT_TYPE",
            "field": "result.type",
            "message": f"Unsupported result type: {request.result.type!r}. "
                       f"Expected one of: {', '.join(sorted(TYPE_SPECIFIC_LABELS))}.",
        })
        return problems

    received = request.sections.type_specific.fields or {}
    received_norm = {_norm(k): k for k in received}

    for label in expected:
        if label in received:
            continue
        near = received_norm.get(_norm(label))
        if near is not None:
            problems.append({
                "code": "LABEL_MISMATCH",
                "field": f"sections.type_specific.fields['{label}']",
                "message": f"Expected label {label!r} but received {near!r}. "
                           "Labels must match the agreed text exactly.",
            })
        else:
            problems.append({
                "code": "MISSING_LABEL",
                "field": f"sections.type_specific.fields['{label}']",
                "message": f"Required field {label!r} is missing for result type "
                           f"{request.result.type!r}.",
            })

    for key in received:
        if key not in expected and _norm(key) not in {_norm(e) for e in expected}:
            problems.append({
                "code": "UNEXPECTED_LABEL",
                "field": f"sections.type_specific.fields['{key}']",
                "message": f"Unexpected field {key!r} for result type "
                           f"{request.result.type!r}.",
            })

    # Closed vocabularies - wrong values are as damaging as missing ones.
    delivery = received.get("Delivery method")
    if delivery is not None and delivery not in DELIVERY_METHODS:
        problems.append({
            "code": "INVALID_VALUE",
            "field": "sections.type_specific.fields['Delivery method']",
            "message": f"{delivery!r} is not a catalog value. Expected one of: "
                       f"{', '.join(DELIVERY_METHODS)}.",
        })

    length = received.get("Length of training")
    if length is not None and length not in TRAINING_LENGTHS:
        problems.append({
            "code": "INVALID_VALUE",
            "field": "sections.type_specific.fields['Length of training']",
            "message": f"{length!r} is not a catalog value. Expected one of: "
                       f"{', '.join(TRAINING_LENGTHS)}.",
        })

    for i, ia in enumerate(request.impact_areas or []):
        if ia.name not in IMPACT_AREAS:
            problems.append({
                "code": "INVALID_VALUE",
                "field": f"impact_areas[{i}].name",
                "message": f"{ia.name!r} is not one of the five impact areas.",
            })
            continue
        for sub in ia.subcomponents:
            if sub not in SUBCOMPONENTS[ia.name]:
                problems.append({
                    "code": "INVALID_VALUE",
                    "field": f"impact_areas[{i}].subcomponents",
                    "message": f"{sub!r} is not a subcomponent of {ia.name!r}. "
                               f"Expected one of: {', '.join(SUBCOMPONENTS[ia.name])}.",
                })

    for i, ev in enumerate(request.sections.evidence):
        for tag in ev.tags:
            if tag not in EVIDENCE_TAGS:
                problems.append({
                    "code": "INVALID_VALUE",
                    "field": f"sections.evidence[{i}].tags",
                    "message": f"{tag!r} is not a catalog evidence tag. "
                               f"Expected one of: {', '.join(EVIDENCE_TAGS)}.",
                })

    return problems
