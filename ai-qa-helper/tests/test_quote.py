from app.signal.quote import is_quote_in_evidence

EVIDENCE = (
    "The project trained 1,200 women farmers in climate‑smart\n"
    "practices, and   “gender‑responsive extension” was adopted by 3 districts."
)


def test_matches_across_whitespace_case_quotes_and_dashes():
    assert is_quote_in_evidence('"Gender-responsive extension" was adopted by 3 districts', EVIDENCE)
    assert is_quote_in_evidence("trained 1,200 women farmers in climate-smart practices", EVIDENCE)


def test_rejects_quotes_not_in_evidence():
    assert not is_quote_in_evidence("trained 5,000 women farmers in climate-smart practices", EVIDENCE)


def test_rejects_quotes_too_short_to_be_evidence():
    assert not is_quote_in_evidence("women", EVIDENCE)
    assert not is_quote_in_evidence("", EVIDENCE)
