"""Deterministic signal (agreement + evidence). The model never decides the colour.

  - green: same value as reported, with a verified quote and complete evidence
  - amber: off by one, no verified quote, partial evidence, or nothing reported to compare
  - red:   off by two or more (0<->2 for Impact Areas), with a verified quote
"""

from dataclasses import dataclass

from app.contract.fields import FieldSpec
from app.contract.messages import Signal


@dataclass(frozen=True)
class SignalInput:
    spec: FieldSpec
    reported: int | None
    """Value the submitter reported in PRMS; None when not reported."""
    suggested: int
    """Value the model proposes."""
    quote_verified: bool
    """The model's quote was found (normalised) in the evidence."""
    partial_evidence: bool
    """Only part of the evidence could be read (e.g. some links private)."""


def compute_signal(inp: SignalInput) -> Signal:
    s = inp.suggested
    if isinstance(s, bool) or not isinstance(s, int) or s < inp.spec.min or s > inp.spec.max:
        raise ValueError(f"suggested value {s!r} outside [{inp.spec.min}, {inp.spec.max}]")
    if not inp.quote_verified or inp.reported is None:
        return "amber"
    diff = abs(s - inp.reported)
    if diff >= 2:
        return "red"
    if diff == 1 or inp.partial_evidence:
        return "amber"
    return "green"
