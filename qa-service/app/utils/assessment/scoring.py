"""
Score (0-100) for the W3/Bilateral quality assessment.

The QA criteria document produces flags and colours, not numbers, so the score is
a derived figure. It is built to satisfy three properties the Reporting Tool needs,
each checked by `verify_properties()`:

  1. MONOTONIC   - fixing any flagged criterion strictly raises the score.
                   Nothing a user fixes can ever lower it.
  2. BANDED      - the score can never contradict the colour:
                       RED   -> 0-49
                       AMBER -> 50-99
                       GREEN -> 100
                   so a red result never outscores an amber one.
  3. WEIGHTED    - a core flag costs more than a non-core flag, matching the
                   criteria document, where only core fields can force RED.

Criteria that were not evaluated (grey: confidential evidence, blocked links)
are excluded from both numerator and denominator, so unevaluable evidence does
not silently depress the score.
"""

from typing import List, Optional

from app.utils.assessment.aggregation import Finding, Outcome, Verdict

CORE_WEIGHT = 3
NON_CORE_WEIGHT = 1

EVALUATED = (Outcome.PASSED, Outcome.FLAGGED)


def _weight(finding: Finding) -> int:
    return CORE_WEIGHT if finding.core else NON_CORE_WEIGHT


def score(findings: List[Finding], verdict: Verdict) -> Optional[int]:
    """None when nothing could be evaluated - no number is better than a fake 0."""
    evaluated = [f for f in findings if f.outcome in EVALUATED]
    if not evaluated:
        return None

    if verdict == Verdict.GREEN:
        return 100

    if verdict == Verdict.NOT_EVALUATED:
        return None

    if verdict == Verdict.AMBER:
        # No core flags by definition. Spread over the non-core criteria only.
        pool = [f for f in evaluated if not f.core]
        flagged = sum(1 for f in pool if f.is_flag)
        ratio = 1 - (flagged / len(pool)) if pool else 0
        return 50 + round(49 * ratio)

    # RED - weighted over everything evaluated.
    max_cost = sum(_weight(f) for f in evaluated)
    cost = sum(_weight(f) for f in evaluated if f.is_flag)
    ratio = 1 - (cost / max_cost) if max_cost else 0
    return round(49 * ratio)


def verify_properties(findings: List[Finding], sections) -> None:
    """Assert monotonicity and banding for one assessment. Used in tests."""
    from app.utils.assessment.aggregation import aggregate

    base = aggregate(findings, sections)
    base_score = score(base.findings, base.overall)
    if base_score is None:
        return

    band = {Verdict.RED: (0, 49), Verdict.AMBER: (50, 99), Verdict.GREEN: (100, 100)}
    lo, hi = band[base.overall]
    if not lo <= base_score <= hi:
        raise AssertionError(
            f"Band violated: {base.overall.value} scored {base_score}, expected {lo}-{hi}"
        )

    # Fixing any single flag must strictly raise the score.
    for i, f in enumerate(findings):
        if not f.is_flag:
            continue
        fixed = list(findings)
        fixed[i] = Finding(f.criterion_id, Outcome.PASSED, core=f.core)
        after = aggregate(fixed, sections)
        after_score = score(after.findings, after.overall)
        if after_score is None or after_score <= base_score:
            raise AssertionError(
                f"Monotonicity violated fixing {f.criterion_id}: "
                f"{base_score} ({base.overall.value}) -> {after_score} ({after.overall.value})"
            )
