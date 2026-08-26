INNOVATION_USE_SECTION = """
⸻

Additional Requirements for "Innovation Use"

Indicator definition:
    • Evidence that an innovation is being used, adopted, or scaled by intended users or beneficiaries — progress along an impact pathway beyond development alone.
    • In PRMS this is an Outcome — it tracks increased use of an innovation by CGIAR, partners, or target beneficiaries over time.
    • Purpose in reporting: capture who uses the innovation (actors and organizations) and optional quantitative measures of use (hectares, households, tons, etc.).

Type-specific block: innovation_use (object, required for this indicator when type-specific data exists)

current_innovation_use_numbers (object inside innovation_use)

innov_use_to_be_determined (boolean, required inside current_innovation_use_numbers)
    • true — innovation use is not yet determined from sources; do not include actors, organization, or measures.
    • false — at least one of actors, organization, or measures must be included.

actors (array inside current_innovation_use_numbers)
    • Include when sources describe groups of people using the innovation and innov_use_to_be_determined is false.
    • Each item represents one actor group. Return actor_type_id and actor_type_name together; must be one of:
        • id 1, name "Farmers/ (agro)pastoralist/ herders/ fishers"
        • id 2, name "Researchers"
        • id 3, name "Extension agents"
        • id 4, name "Policy actors (public or private)"
        • id 5, name "Other"
    • When actor_type_id = 5, include other_actor_type describing the specific actor group.
    • sex_and_age_disaggregation (boolean) — set true when sources provide gender and/or youth breakdown for the group.
    • When sex_and_age_disaggregation = true, include how_many (total for the group) and any supported counts: women, women_youth, men, men_youth.
    • Youth = ages 15 to 24; non-youth = older than 24.
    • Omit unsupported count fields rather than inventing them.

organization (array inside current_innovation_use_numbers)
    • Include when sources describe types of organizations or institutions using the innovation and innov_use_to_be_determined is false.
    • Each item must include institution_types_id from the catalog below.
    • When the selected type belongs to a parent category, also include organization_type with the parent name and institution_types_id with the subtype code.
    • When the type has no parent category (ids 75, 76, 77, 78), include only institution_types_id.
    • Include how_many when the number of organizations is stated.
    • When institution_types_id = 78, include other_institution describing the organization type.

    Parent organization_type "NGO" — subtype institution_types_id options:
        • id 39, name "NGO International (General)"
        • id 40, name "NGO International (Farmers)"
        • id 42, name "NGO Regional (General)"
        • id 43, name "NGO Regional (Farmers)"
        • id 45, name "NGO National (General)"
        • id 46, name "NGO National (Farmers)"
        • id 48, name "NGO Local (General)"
        • id 49, name "NGO Local (Farmers)"

    Parent organization_type "Research organizations and universities" — subtype institution_types_id options:
        • id 52, name "Research organizations and universities International (General)"
        • id 53, name "Research organizations and universities International (Universities)"
        • id 54, name "Research organizations and universities International (CGIAR)"
        • id 56, name "Research organizations and universities Regional (NA)"
        • id 57, name "Research organizations and universities Regional (Universities)"
        • id 59, name "Research organizations and universities National (NARS)"
        • id 60, name "Research organizations and universities National (Universities)"
        • id 62, name "Research organizations and universities Local (NA)"
        • id 63, name "Research organizations and universities Local (Universities)"

    Parent organization_type "Organization (other than financial or research)" — subtype institution_types_id options:
        • id 65, name "Organization (other than financial or research) International"
        • id 66, name "Organization (other than financial or research) Regional"

    Parent organization_type "Government" — subtype institution_types_id options:
        • id 68, name "Government (National)"
        • id 69, name "Government (Subnational)"

    Parent organization_type "Financial institution" — subtype institution_types_id options:
        • id 71, name "Financial Institution International"
        • id 72, name "Financial Institution Regional"
        • id 73, name "Financial Institution National"
        • id 74, name "Financial Institution Local"

    Types without organization_type — institution_types_id only:
        • id 75, name "Private company (other than financial)"
        • id 76, name "Public-Private Partnership"
        • id 77, name "Foundation"
        • id 78, name "Other"

measures (array inside current_innovation_use_numbers)
    • Include when sources provide quantitative measures of innovation use (hectares, households, tons, units deployed, etc.) and innov_use_to_be_determined is false.
    • Each item must include unit_of_measure.
    • Include quantity when a numeric amount is stated.

Example:
{
    "innovation_use": {
        "current_innovation_use_numbers": {
            "innov_use_to_be_determined": false,
            "actors": [
                {
                    "actor_type_id": 1,
                    "actor_type_name": "Farmers/ (agro)pastoralist/ herders/ fishers",
                    "sex_and_age_disaggregation": true,
                    "how_many": 120,
                    "women": 60,
                    "women_youth": 25,
                    "men": 40,
                    "men_youth": 15
                },
                {
                    "actor_type_id": 5,
                    "actor_type_name": "Other",
                    "other_actor_type": "Local agribusinesses",
                    "sex_and_age_disaggregation": false
                }
            ],
            "organization": [
                {
                    "organization_type": "NGO",
                    "institution_types_id": 45,
                    "how_many": 3
                },
                {
                    "institution_types_id": 75,
                    "how_many": 2
                },
                {
                    "institution_types_id": 78,
                    "other_institution": "Farmer cooperatives",
                    "how_many": 1
                }
            ],
            "measures": [
                {"unit_of_measure": "hectares", "quantity": "2500"},
                {"unit_of_measure": "households", "quantity": "800"}
            ]
        }
    }
}
"""
