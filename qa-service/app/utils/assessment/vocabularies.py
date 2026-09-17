"""
Closed vocabularies for W3/Bilateral results, confirmed by the Reporting Tool
(contract v0.2). These are seeded catalogs, not free text, so they can be
validated exactly rather than matched loosely.
"""

# --------------------------------------------------------------------------- #
# Impact areas
# --------------------------------------------------------------------------- #

GENDER = "Gender equality, youth and social inclusion"
CLIMATE = "Climate adaptation and mitigation"
NUTRITION = "Nutrition, health and food security"
ENVIRONMENT = "Environmental health and biodiversity"
POVERTY = "Poverty reduction, livelihoods and jobs"

IMPACT_AREAS = (GENDER, CLIMATE, NUTRITION, ENVIRONMENT, POVERTY)

SUBCOMPONENTS = {
    GENDER: ("Gender equality", "Youth", "Social Inclusion"),
    CLIMATE: ("Adaptation", "Mitigation"),
    NUTRITION: ("Nutrition", "Health", "Food Security"),
    ENVIRONMENT: ("Environmental health", "Biodiversity"),
    POVERTY: ("Poverty Reduction", "Livelihoods", "Jobs"),
}

# --------------------------------------------------------------------------- #
# Evidence tags -> impact area
# --------------------------------------------------------------------------- #

EVIDENCE_TAGS = ("Gender", "Youth", "Nutrition", "Environment & biodiversity", "Poverty")

# The two vocabularies are NOT symmetric, and the asymmetry breaks one criterion:
#   - "Youth" is an evidence tag but not a pillar. It is seeded as a subcomponent
#     of Gender, so a Youth-tagged item is Gender-specific evidence.
#   - "Climate adaptation and mitigation" is a pillar with NO evidence tag, so no
#     evidence item can ever be marked climate-specific.
TAG_TO_IMPACT_AREA = {
    "Gender": GENDER,
    "Youth": GENDER,
    "Nutrition": NUTRITION,
    "Environment & biodiversity": ENVIRONMENT,
    "Poverty": POVERTY,
}

# Impact areas that no evidence tag can point at. The "score = 2 requires an
# IA-specific evidence item" criterion cannot be satisfied for these, so it must
# not be evaluated for them - otherwise every result scoring Climate = 2 gets a
# flag it has no way to clear.
IMPACT_AREAS_WITHOUT_TAG = tuple(
    area for area in IMPACT_AREAS if area not in TAG_TO_IMPACT_AREA.values()
)


def evidence_supports_impact_area(tags, impact_area: str) -> bool:
    """True if any tag on an evidence item points at this impact area."""
    return any(TAG_TO_IMPACT_AREA.get(t) == impact_area for t in tags or ())


# --------------------------------------------------------------------------- #
# Delivery method (Capacity Sharing)
# --------------------------------------------------------------------------- #

DELIVERY_VIRTUAL = "Virtual / Online"
DELIVERY_IN_PERSON = "In person"
DELIVERY_BLENDED = "Blended (in-person and virtual)"

DELIVERY_METHODS = (DELIVERY_VIRTUAL, DELIVERY_IN_PERSON, DELIVERY_BLENDED)

# Only fully virtual delivery waives the geographic requirement. Blended keeps an
# in-person component, so geography stays required.
# Must be an EXACT match: "Blended (in-person and virtual)" contains the substring
# "virtual", so any contains/startswith test wrongly exempts it.
GEOGRAPHY_EXEMPT_DELIVERY = (DELIVERY_VIRTUAL,)


def waives_geography(delivery_method: str) -> bool:
    return delivery_method in GEOGRAPHY_EXEMPT_DELIVERY


# --------------------------------------------------------------------------- #
# Length of training (Capacity Sharing)
# --------------------------------------------------------------------------- #

LENGTH_LONG_TERM = "Long-term"
LENGTH_SHORT_TERM = "Short-term"
TRAINING_LENGTHS = (LENGTH_LONG_TERM, LENGTH_SHORT_TERM)


# --------------------------------------------------------------------------- #
# type_specific.fields labels, exact text, per result type
# --------------------------------------------------------------------------- #

TYPE_SPECIFIC_LABELS = {
    "policy change": ("Policy type", "Policy stage", "Implementing organizations", "USD amount"),
    "innovation use": ("User types", "Number of people using", "Other quantitative measures", "Investment (USD)"),
    "capacity sharing for development": ("Number of people trained", "Length of training", "Delivery method", "Implementing organizations"),
    "innovation development": ("Innovation typology", "Readiness level", "Innovation developers"),
    "other output": (),
    "other outcome": (),
}

# Labels that arrive but carry no QA criterion in the criteria document. Passed to
# the model as context; never flagged.
LABELS_WITHOUT_CRITERIA = {
    "policy change": ("USD amount",),
    "capacity sharing for development": ("Implementing organizations",),
}
