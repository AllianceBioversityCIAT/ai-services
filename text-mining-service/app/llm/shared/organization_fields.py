"""Post-mapping cleanup for organization fields on mining results."""

from app.utils.logger.logger_util import get_logger

logger = get_logger()

SIMILARITY_THRESHOLD = 70.0


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
