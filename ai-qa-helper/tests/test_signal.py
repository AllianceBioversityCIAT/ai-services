import pytest

from app.contract.fields import AI_FIELDS
from app.signal.signal import SignalInput, compute_signal

IA = AI_FIELDS["impact_area_gender"]
IRL = AI_FIELDS["innovation_readiness_level"]


def sig(spec, reported, suggested, quote_verified=True, partial_evidence=False):
    return compute_signal(SignalInput(spec, reported, suggested, quote_verified, partial_evidence))


@pytest.mark.parametrize(
    ("spec", "reported", "suggested", "expected"),
    [
        (IA, 1, 1, "green"),
        (IA, 1, 2, "amber"),
        (IA, 0, 1, "amber"),
        (IA, 0, 2, "red"),
        (IA, 2, 0, "red"),
        (IRL, 5, 5, "green"),
        (IRL, 5, 6, "amber"),
        (IRL, 5, 3, "red"),
        (IRL, 2, 9, "red"),
    ],
)
def test_table(spec, reported, suggested, expected):
    assert sig(spec, reported, suggested) == expected


def test_amber_without_verified_quote_even_when_agreeing_or_far():
    assert sig(IA, 1, 1, quote_verified=False) == "amber"
    assert sig(IA, 0, 2, quote_verified=False) == "amber"


def test_partial_evidence_downgrades_agreement_but_keeps_red():
    assert sig(IA, 1, 1, partial_evidence=True) == "amber"
    assert sig(IA, 0, 2, partial_evidence=True) == "red"


def test_amber_when_nothing_reported():
    assert sig(IRL, None, 4) == "amber"


def test_rejects_out_of_range_or_non_integer():
    with pytest.raises(ValueError):
        sig(IA, 1, 3)
    with pytest.raises(ValueError):
        sig(IRL, 1, 1.5)
