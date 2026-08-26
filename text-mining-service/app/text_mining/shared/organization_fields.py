"""Post-mapping cleanup for organization fields on mining results."""

from __future__ import annotations

from typing import Any

from app.utils.logger.logger_util import get_logger

logger = get_logger()

SIMILARITY_THRESHOLD = 70.0
PRMS_INSTITUTION_SIMILARITY_THRESHOLD = 80.0


def normalize_similarity_score(score: Any) -> float:
    """Normalize mapping scores to a 0–100 percentage scale."""
    if score is None:
        return 0.0
    try:
        value = float(score)
    except (TypeError, ValueError):
        return 0.0
    if 0.0 <= value <= 1.0:
        value *= 100.0
    return value


def _finalize_mds_institution(
    item: dict[str, Any],
    *,
    id_key: str,
    name_key: str,
    acronym_key: str,
) -> dict[str, Any] | None:
    score = normalize_similarity_score(item.get("similarity_score", 0))
    extraction_name = item.pop("_extraction_name", None)
    extraction_acronym = item.pop("_extraction_acronym", None)
    item.pop("_lookup_label", None)
    item.pop("similarity_score", None)

    mapped_id = item.get(id_key)
    if mapped_id is not None and score >= PRMS_INSTITUTION_SIMILARITY_THRESHOLD:
        result: dict[str, Any] = {id_key: int(mapped_id)}
        if acronym := item.get(acronym_key):
            result[acronym_key] = acronym
        if name := item.get(name_key):
            result[name_key] = name
        return result

    result = {}
    if extraction_name:
        result[name_key] = extraction_name
    if extraction_acronym:
        result[acronym_key] = extraction_acronym
    return result or None


def clean_prms_institution_fields(mining_result: dict[str, Any]) -> None:
    """
    Finalize PRMS partner / implementing-organization items after OpenSearch mapping.

    Mapped (score >= 80%): id + canonical acronym + name.
    Unmapped: only the extracted name or acronym — no id, no similarity_score.
    """
    partners = mining_result.get("contributing_partners")
    if isinstance(partners, list):
        cleaned_partners = []
        for item in partners:
            if not isinstance(item, dict):
                continue
            finalized = _finalize_mds_institution(
                dict(item),
                id_key="institution_id",
                name_key="name",
                acronym_key="acronym",
            )
            if finalized:
                cleaned_partners.append(finalized)
        if cleaned_partners:
            mining_result["contributing_partners"] = cleaned_partners
        else:
            mining_result.pop("contributing_partners", None)

    policy_change = mining_result.get("policy_change")
    if isinstance(policy_change, dict):
        organizations = policy_change.get("implementing_organization")
        if isinstance(organizations, list):
            cleaned_orgs = []
            for item in organizations:
                if not isinstance(item, dict):
                    continue
                finalized = _finalize_mds_institution(
                    dict(item),
                    id_key="institutions_id",
                    name_key="institutions_name",
                    acronym_key="institutions_acronym",
                )
                if finalized:
                    cleaned_orgs.append(finalized)
            if cleaned_orgs:
                policy_change["implementing_organization"] = cleaned_orgs
            else:
                policy_change.pop("implementing_organization", None)


def clean_organization_fields(mining_result: dict) -> None:
    """
    Clean organization fields based on mapping success:
    - If name + id + similarity > threshold → keep ONLY name, id, similarity_score
    - If name + id but similarity <= threshold, and has type → keep ONLY type, sub_type, other_type
    - If name but no id, and has type → keep ONLY type, sub_type, other_type
    - If only type (no name) → keep ONLY type, sub_type, other_type
    - Otherwise → remove organization
    """
    if "organizations_detailed" not in mining_result:
        return

    organizations = mining_result.get("organizations_detailed", [])
    cleaned_organizations = []

    for org in organizations:
        has_name = org.get("institution_name") is not None and org.get("institution_name").strip() != ""
        has_id = org.get("institution_id") is not None and org.get("institution_id") != ""
        has_type = org.get("type") is not None and org.get("type").strip() != ""
        similarity = org.get("similarity_score", 0)

        if has_name and has_id and similarity > SIMILARITY_THRESHOLD:
            cleaned_org = {
                "institution_name": org["institution_name"],
                "institution_id": org["institution_id"],
                "similarity_score": similarity,
            }
            cleaned_organizations.append(cleaned_org)
            logger.info(
                "✅ Organization mapped: '%s' → ID: %s (score: %s)",
                org["institution_name"],
                org["institution_id"],
                similarity,
            )

        elif has_name and has_id and similarity <= SIMILARITY_THRESHOLD and has_type:
            cleaned_org = {"type": org["type"]}
            if org.get("sub_type"):
                cleaned_org["sub_type"] = org["sub_type"]
            if org.get("other_type"):
                cleaned_org["other_type"] = org["other_type"]
            cleaned_organizations.append(cleaned_org)
            logger.warning(
                "⚠️ Organization '%s' mapped with low similarity (%s), using type classification: %s",
                org["institution_name"],
                similarity,
                org["type"],
            )

        elif has_name and has_id and similarity <= SIMILARITY_THRESHOLD and not has_type:
            logger.warning(
                "❌ Organization '%s' mapped with low similarity (%s) and no type classification - discarding",
                org["institution_name"],
                similarity,
            )
            continue

        elif has_name and not has_id and has_type:
            cleaned_org = {"type": org["type"]}
            if org.get("sub_type"):
                cleaned_org["sub_type"] = org["sub_type"]
            if org.get("other_type"):
                cleaned_org["other_type"] = org["other_type"]
            cleaned_organizations.append(cleaned_org)
            logger.info(
                "ℹ️ Organization '%s' not mapped, using type classification: %s",
                org["institution_name"],
                org["type"],
            )

        elif has_name and not has_id and not has_type:
            logger.warning(
                "❌ Organization '%s' not mapped and no type provided - discarding",
                org["institution_name"],
            )
            continue

        elif not has_name and has_type:
            cleaned_org = {"type": org["type"]}
            if org.get("sub_type"):
                cleaned_org["sub_type"] = org["sub_type"]
            if org.get("other_type"):
                cleaned_org["other_type"] = org["other_type"]
            cleaned_organizations.append(cleaned_org)
            logger.info("ℹ️ Organization (no name) with type: %s", org["type"])

        else:
            logger.warning("❌ Organization with neither name nor type - discarding")
            continue

    if cleaned_organizations:
        mining_result["organizations_detailed"] = cleaned_organizations
        logger.info(
            "🧹 Cleaned organizations: %s → %s",
            len(organizations),
            len(cleaned_organizations),
        )
    else:
        mining_result.pop("organizations_detailed", None)
        logger.info("🧹 All organizations removed - no valid data")
