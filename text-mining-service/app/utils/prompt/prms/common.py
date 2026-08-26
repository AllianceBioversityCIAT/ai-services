COMMON_RULES = """
Analyze the provided source excerpts and extract all results related ONLY to these indicators:
    • "Capacity Sharing for Development"
    • "Policy Change"
    • "Innovation Development"
    • "Innovation Use"
    • "Other Output"
    • "Other Outcome"

Do NOT identify or return Knowledge Product results.
Do NOT extract Theory of Change (ToC) fields, toc_mapping, contributing_programs, or impact area scores.
Do NOT extract identity/audit fields (created_by, submitted_by, created_date, contributing_bilateral_projects).
If source content only supports Knowledge Products, or no supported result is found, return:
{
    "results": []
}

Source roles:
    • Documents may identify candidates and are eligible as formal evidence candidates.
    • Free text and audio transcripts may identify and pre-fill candidate drafts, but are NEVER formal evidence.
    • Do not claim free text or audio is documentary evidence.

General rules:
    • Do not fabricate fields unsupported by the sources.
    • Separate multiple results even if they share a source.
    • Do not merge results solely because titles or keywords are similar.
    • Use exact indicator discriminator values listed above.
    • Omit unsupported optional fields rather than inventing defaults.
    • Return raw JSON only — no markdown fences, no prose outside JSON.
"""

PRMS_INDICATOR_CONTEXT = """
⸻

PRMS indicator context (for classification only)

In PRMS, results are grouped as Outputs or Outcomes:
    • Outputs: "Capacity Sharing for Development", "Innovation Development", "Other Output"
    • Outcomes: "Policy Change", "Innovation Use", "Other Outcome"

Use this framing to choose the correct indicator discriminator. "Other Output" and "Other Outcome" are distinct — never combine them. A single source may support multiple results of different types.

How to distinguish Output vs Outcome:
    • An **Output** is a deliverable, product, service, method, or tangible contribution produced by the project (something created or delivered).
    • An **Outcome** is a change, effect, or result observed in people, institutions, or systems attributable to the work (something that changed because of the work).
    • If sources describe a change in behavior, capacity, adoption, or policy environment, prefer an Outcome indicator (Policy Change, Innovation Use, or "Other Outcome").
    • If sources only describe a document, report, tool, or deliverable produced — without describing a change that occurred — prefer an Output indicator (Capacity Sharing for Development, Innovation Development, or "Other Output").

When writing title and description for any result:
    • title: concise, informative, usable as stand-alone information (max ~30 words when possible); state what the result is, who is involved, and where relevant when the sources support it.
    • description: clear for a non-specialist audience (max ~150 words when possible); add background or contribution context not already captured in the title.
"""

COMMON_MDS_FIELDS = """
⸻

General Information Fields (apply to every result)

Result Title
    • title — exact or concise inferred title from sources.

Result Description
    • description — brief description of the result.

Lead Center
    • lead_center — object; include when the sources identify the lead CGIAR/Alliance center.
    • It should be the center that is responsible for the result and/or the center that is the main funder of the result.
    • Must be exactly one center from the CGIAR CENTERS REFERENCE DATA section in the prompt.
    • Return all three fields exactly as listed: institution_id (number), acronym (string), name (string).
    • Example: {"institution_id": 1279, "acronym": "ICARDA", "name": "International Center for Agricultural Research in the Dry Areas"}
    • Omit the entire object if the lead center cannot be matched to the reference list.

Geographic focus
    • geo_focus — object; include when geography is known.
    • scope_label — must be one of:
        • "Global": if the sources do not specify a region or country.
        • "Regional": if the sources mention ONLY the region, but do not specify countries. If the sources specify countries within the region, it should be classified as "National".
        • "National": if the sources mention one or more countries, but do not specify sub-national areas.
        • "Sub-national": if the sources mention specific locations within a country.
        • "This is yet to be determined"
    • scope_code - always a number:
        • 1: if scope_label is "Global"
        • 2: if scope_label is "Regional"
        • 4: if scope_label is "National"
        • 5: if scope_label is "Sub-national"
        • 50: if scope_label is "This is yet to be determined"
    • regions and countries (inside geo_focus):
        • Resolve location names from sources to official codes using the GEOGRAPHIC REFERENCE DATA section in the prompt when available.
        • Return codes ONLY — do not include name fields for regions or countries.
        • If scope_label = "Global", do NOT include regions or countries.
        • If scope_label = "Regional", return regions[] with the appropriate UN M49 region code(s) as numbers:
            (e.g., regions: [{"um49code": 150}, {"um49code": 2}]).
        • If scope_label = "National", return countries[] with objects containing the ISO Alpha-2 country code(s):
            (e.g., countries: [{"iso_alpha_2": "KE"}, {"iso_alpha_2": "UG"}]).
        • If scope_label = "Sub-national", return countries[] as an array of objects; each object contains iso_alpha_2 and subnational_areas (ISO 3166-2 codes):
            Use your knowledge of ISO 3166-2 subnational codes to provide the appropriate codes based on the location names mentioned in the sources:
            (e.g., countries: [{"iso_alpha_2": "CO", "subnational_areas": ["CO-CUN", "CO-CAS"]}]).
        • If not applicable, do not return regions or countries in geo_focus.

Contributing centers
    • contributing_center — array; include when sources mention other CGIAR/Alliance centers contributing.
    • Each item must be one center from the CGIAR CENTERS REFERENCE DATA section in the prompt.
    • Return all three fields exactly as listed: institution_id, acronym, name.
    • Example: [{"institution_id": 115, "acronym": "CIFOR", "name": "Center for International Forestry Research"}, {"institution_id": 1279, "acronym": "ICARDA", "name": "International Center for Agricultural Research in the Dry Areas"}]
    • Omit the array if no contributing centers from the reference list are supported (do not invent).

Contributing partners
    • contributing_partners — array; include when sources mention non-CGIAR partner institutions.
    • Refers to the partner(s) that made a significant contribution to the achievement of the result that is being submitted.
    • These are organizations that contribute to, support, or collaborate in conducting the training or capacity building activity.
    • IMPORTANT: Do not confuse with trainees organizations. Partners contribute TO the training, while trainees organizations are represented BY the attendees.
    • These are external partners — do NOT use the CGIAR centers reference list.
    • Return the partner name or acronym as extracted from sources.
    • Each item must contain exactly one of: name or acronym.
    • Example: [{"name": "National Agricultural Research Organization"}, {"acronym": "NARO"}]
    • If there are multiple partners, list each one as a separate object in the array.
    • Omit the array if not supported (do not invent).

Evidence
    • evidence — array of objects with link (URI string, required per item) and optional description.
    • Refers to the supporting materials or documentation that validate the training activities and outcomes.
    • Include ONLY when the sources contain an explicit URL/link (typically from documents).
    • Example: [{"link": "https://example.org/report.pdf", "description": "Workshop report"}]
    • Omit the array if no explicit links are present.
"""

OUTPUT_SCHEMA_FRAGMENT = """
⸻

Output Format

Return dates in YYYY-MM-DD format when available.
For partial or missing participant data, follow the partial participant rule above.
Your output must be a single valid JSON object with a results array, and must not include any additional text, comments, footnotes, citations, or explanations.

Required and mandatory fields:
• indicator
• title
• description
• geo_focus

Do not:
• Add text before or after the JSON.
• Add any explanatory sentences, notes, or references (e.g., "This result is extracted from…").
• Include markdown code blocks like ```json or ```.
• Escape quotes unless necessary.
• Wrap the JSON in additional quotes or strings.
• Include fields with null values - omit them completely.
• Omit unsupported fields entirely.
• Return Knowledge Product, ToC, or impact area fields.

The response must be raw JSON only — nothing else.

Indicator discriminator must be exactly one of:
• "Capacity Sharing for Development"
• "Policy Change"
• "Innovation Development"
• "Innovation Use"
• "Other Output"
• "Other Outcome"

⸻
Follow this envelope for every result in results[]:

{
    "results": [
        {
            "indicator": "<one of the six supported indicators>",
            "title": "<result title>",
            "description": "<result description>",
            "lead_center": {
                "institution_id": <id_number>,
                "acronym": <acronym_string>,
                "name": <name_string>
            },
            "geo_focus": {
                "scope_code": <scope_code_number>,
                "scope_label": <scope_label_string>,
                "countries": [{"iso_alpha_2": <iso_alpha_2_string>, "subnational_areas": [<subnational_area_string>]}
            },
            "contributing_center": [
                {
                    "institution_id": <id_number>,
                    "acronym": <acronym_string>,
                    "name": <name_string>
                }
            ],
            "contributing_partners": [{"name": "<partner name>"}, {"acronym": "<partner acronym>"}],
            "evidence": [{"link": "https://...", "description": "<string>"}]
        }
    ]
}

Common fields above apply to every indicator when supported by sources. Omit optional objects or arrays entirely when not supported.

Type-specific block (at most one per result — include only the block that matches indicator):
    • "Capacity Sharing for Development" → capacity_sharing
    • "Policy Change" → policy_change
    • "Innovation Development" → innovation_development
    • "Innovation Use" → innovation_use
    • "Other Output" → none
    • "Other Outcome" → none

Each indicator section above includes the field rules and a worked example for its type-specific block. Combine that block with the common envelope shown here — do not copy fields from a different indicator type.
"""
