from app.text_mining.shared.json_parser import extract_json_object, is_valid_json


def test_extract_json_object_recovers_embedded_json_without_repair():
    raw = (
        "I'll work through each result systematically.\n\n"
        '{"results": [{"indicator": "Policy Change", "title": "Budget policy", '
        '"description": "desc", "geo_focus": {"scope_label": "Global"}}]}'
    )
    extracted = extract_json_object(raw)
    assert is_valid_json(extracted)


def test_extract_json_object_from_markdown_fence():
    raw = 'Here is the JSON:\n```json\n{"results": []}\n```\nDone.'
    extracted = extract_json_object(raw)
    assert extracted == '{"results": []}'


def test_extract_json_object_prefers_results_envelope():
    raw = 'Notes {"other": 1} {"results": [{"indicator": "Other Output", "title": "t", "description": "d", "geo_focus": {"scope_label": "Global"}}]}'
    extracted = extract_json_object(raw)
    payload = __import__("json").loads(extracted)
    assert payload["results"][0]["indicator"] == "Other Output"
