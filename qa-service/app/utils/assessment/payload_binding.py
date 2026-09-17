"""
Binds MDS fields from the QA criteria documents to contract v0.1 payload paths.

This is the single point where the Reporting Tool's JSON shape is known. Every
other module works off `criteria_catalog` ids, so a contract change touches only
this file.

UNBOUND marks a criterion the contract cannot currently feed.
"""

from typing import Optional

UNBOUND = None

# MDS field (as written in the criteria document) -> payload path
FIELD_BINDINGS = {
    # --- generic, all indicator types -------------------------------------
    "Title": "sections.general_information.title",
    "Result description": "sections.general_information.description",
    "ToC link (SP/A)": "sections.contributors_and_partners.theory_of_change",
    "Internal collaboration": (
        "sections.contributors_and_partners.{lead_center,contributing_centers,"
        "lead_project,contributing_projects}"
    ),
    "Partner collaboration": (
        "sections.contributors_and_partners.{external_partners,no_external_partners}"
    ),
    "Geographic focus": "sections.geographic_location.*",
    "Evidence": "sections.evidence[]",
    "Impact area tags": "impact_areas[]",  # sibling of sections, optional

    # --- type-specific: all arrive as display labels in type_specific.fields
    "Policy type": "sections.type_specific.fields['Policy type']",
    "Policy stage": "sections.type_specific.fields['Policy stage']",
    "Policy owner (implementing org.)": "sections.type_specific.fields['Implementing organizations']",
    "User type": "sections.type_specific.fields['User types']",
    "# people/actors using": "sections.type_specific.fields['Number of people using']",
    "Other quantitative measure": "sections.type_specific.fields['Other quantitative measures']",
    "Estimated USD spend": "sections.type_specific.fields['Investment (USD)']",
    "Result level": "sections.general_information.result_level",
    "# people trained": "sections.type_specific.fields['Number of people trained']",
    "Length of training": "sections.type_specific.fields['Length of training']",  # single term
    "Delivery method": "sections.type_specific.fields['Delivery method']",
    "Innovation type (typology)": "sections.type_specific.fields['Innovation typology']",
    "Innovation Readiness Level (IRL)": "sections.type_specific.fields['Readiness level']",
    "Innovation Developer": "sections.type_specific.fields['Innovation developers']",
    "Evidence (per IRL)": "sections.evidence[]",
    "Result type check": "sections.general_information.{title,description}",
}

# Labels confirmed by the Reporting Tool example payload. Everything else is a
# guess until the per-type enumeration arrives.
# All type_specific labels confirmed by Reporting (contract v0.2). See
# vocabularies.TYPE_SPECIFIC_LABELS for the authoritative per-type list.
CONFIRMED_LABELS = "all"


def binding_for(mds_field: str) -> Optional[str]:
    return FIELD_BINDINGS.get(mds_field, UNBOUND)


def coverage(result_type: str):
    """Report which applicable criteria the contract can and cannot feed."""
    from app.utils.assessment.criteria_catalog import criteria_for

    bound, unbound, tbc = [], [], []
    for c in criteria_for(result_type):
        path = binding_for(c.mds_field)
        if path is UNBOUND:
            unbound.append(c)
        elif "<label TBC>" in path:
            tbc.append(c)
        else:
            bound.append(c)
    return {"bound": bound, "unbound": unbound, "label_tbc": tbc}
