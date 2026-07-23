from unittest.mock import patch

from app.llm.shared.map_fields import clear_mapping_cache, map_fields_with_opensearch
from app.llm.shared.organization_fields import clean_prms_institution_fields


def _map_and_clean(mining_result: dict, entries: list[dict]) -> dict:
    clear_mapping_cache()
    payload = {key: value for key, value in mining_result.items() if not key.startswith("_")}
    with patch("app.llm.shared.map_fields.requests.post") as mock_post:
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = {
            "results": [
                {
                    "original_value": entry["value"],
                    "type": "institution",
                    "mapped_id": entry.get("mapped_id"),
                    "mapped_name": entry.get("mapped_name"),
                    "mapped_acronym": entry.get("mapped_acronym"),
                    "score": entry.get("score", 0),
                }
                for entry in entries
            ]
        }
        mapped = map_fields_with_opensearch(payload, "http://mapping.test")
    clean_prms_institution_fields(mapped)
    return mapped


def test_prms_maps_only_contributing_partners_not_centers():
    mining_result = {
        "lead_center": {
            "institution_id": 1279,
            "acronym": "ICARDA",
            "name": "International Center for Agricultural Research in the Dry Areas",
        },
        "contributing_center": [
            {
                "institution_id": 115,
                "acronym": "CIFOR",
                "name": "Center for International Forestry Research",
            }
        ],
        "contributing_partners": [{"name": "National Agricultural Research Organisation"}],
    }
    entries = [
        {
            "value": "National Agricultural Research Organisation",
            "mapped_id": 999,
            "mapped_name": "National Agricultural Research Organisation",
            "mapped_acronym": "NARO",
            "score": 0.95,
        }
    ]
    original_lead = dict(mining_result["lead_center"])
    original_center = dict(mining_result["contributing_center"][0])

    mapped = _map_and_clean(mining_result, entries)

    assert mapped["lead_center"] == original_lead
    assert mapped["contributing_center"][0] == original_center
    assert mapped["contributing_partners"][0] == {
        "institution_id": 999,
        "acronym": "NARO",
        "name": "National Agricultural Research Organisation",
    }


def test_prms_partner_keeps_extracted_name_when_score_below_threshold():
    mining_result = {
        "contributing_partners": [{"name": "Ministry of Agriculture Kenya"}],
    }
    entries = [
        {
            "value": "Ministry of Agriculture Kenya",
            "mapped_id": 42,
            "mapped_name": "Ministry of Agriculture",
            "mapped_acronym": "MOA",
            "score": 0.75,
        }
    ]

    mapped = _map_and_clean(mining_result, entries)

    assert mapped["contributing_partners"][0] == {"name": "Ministry of Agriculture Kenya"}
    assert "institution_id" not in mapped["contributing_partners"][0]


def test_prms_partner_keeps_extracted_acronym_when_unmapped():
    mining_result = {
        "contributing_partners": [{"acronym": "MoA-Uganda"}],
    }

    mapped = _map_and_clean(mining_result, [])

    assert mapped["contributing_partners"][0] == {"acronym": "MoA-Uganda"}


def test_prms_maps_implementing_organization_in_policy_change():
    mining_result = {
        "policy_change": {
            "implementing_organization": [{"institutions_name": "Ministry of Agriculture Kenya"}],
        },
    }
    entries = [
        {
            "value": "Ministry of Agriculture Kenya",
            "mapped_id": 1279,
            "mapped_name": "Ministry of Agriculture Kenya",
            "mapped_acronym": "MOA",
            "score": 0.92,
        }
    ]

    mapped = _map_and_clean(mining_result, entries)

    assert mapped["policy_change"]["implementing_organization"][0] == {
        "institutions_id": 1279,
        "institutions_acronym": "MOA",
        "institutions_name": "Ministry of Agriculture Kenya",
    }


def test_prms_implementing_organization_keeps_acronym_only_when_unmapped():
    mining_result = {
        "policy_change": {
            "implementing_organization": [{"institutions_acronym": "MoA-Uganda"}],
        },
    }

    mapped = _map_and_clean(mining_result, [])

    assert mapped["policy_change"]["implementing_organization"][0] == {
        "institutions_acronym": "MoA-Uganda",
    }
