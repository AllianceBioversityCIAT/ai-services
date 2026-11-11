from scripts.export_schemas import render


def test_published_contract_is_up_to_date():
    stale = [str(p.name) for p, text in render().items() if not p.exists() or p.read_text() != text]
    assert not stale, f"Regenerate with `uv run python -m scripts.export_schemas`: {stale}"
