COMMON_RULES = """
Analyze the provided source excerpts and extract ONLY the reportable results that the source substantively supports, for these indicators:
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
    • Separate distinct achievements even if they share a source, but report each achievement only ONCE — never return the same event, agreement, deliverable, or change under two different indicators. Choose the single best-fitting indicator.
    • Do not merge results solely because titles or keywords are similar.
    • Use exact indicator discriminator values listed above.
    • Omit unsupported optional fields rather than inventing defaults.
    • Return raw JSON only — no markdown fences, no prose outside JSON.

⸻

Selectivity — quality over quantity

Users review every result you return as a draft. Returning weak results costs them time and erodes trust, so precision matters more than recall. An empty results array is a correct answer when the source has no substantive result.

Return a result ONLY when the source states that the achievement actually happened (delivered, produced, adopted, enacted, changed) and gives concrete detail about it (what, who, where, and — when relevant — how many).

A mention is NOT a result. Do NOT return results for:
    • Plans, intentions, targets, proposals, upcoming or ongoing activities without a completed achievement.
    • Signing of memoranda of understanding (MoUs), collaboration, partnership, grant, funding, or host-country agreements.
    • Project, programme, or initiative launches, inception meetings, kick-offs, and announcements of new funding.
    • Concept notes, proposals, bids, and resource-mobilization figures (amounts raised or awarded to the project itself).
    • Internal governance or management arrangements (steering committees, boards, staffing, office openings).
    • Background, context, or literature statements that are not achievements of the work being reported.
    • A single sentence or figure in a long report that names an activity without describing it.
    • Intermediate research or project steps: experiments, trials, or demonstration sites set up; samples collected or shipped; protocols drafted or under testing; students enrolled; study tours, field visits, or exposure visits. These are activities, not results, unless the source reports a finished product, a completed training with participants, or a measured change.
    • Knowledge gained, lessons learned, or "insights" by the project team itself.
    • Investments, loans, or projects of other organizations that merely include or mention the work, unless the source states that a policy, budget, or investment decision was made because of it — and then report it once, as Policy Change.

How many results to return:
    • Fewer, stronger results are better. Return only the achievements a reviewer would clearly want to report.
    • A short document (about 2–3 pages: a brief, a policy note, a short report) usually supports 1 to 3 results.
    • Long reports (annual, progress, or donor reports) list many activities. Return only the strongest, best-documented achievements — do not turn every paragraph or figure into a result.
    • Do not split one achievement into several results (for example, one programme's trainings by session or district, or one innovation's adoption by country) unless the source reports them as clearly separate achievements.
    • Do not return an aggregate programme-wide figure (total jobs, total people trained, total farmers reached) as a separate result when the specific achievements behind it are already returned.

⸻

Provenance and confidence (required on every result)

    • supporting_quote — a VERBATIM passage copied exactly from the source excerpts (one or two consecutive sentences, ideally 15–60 words) that most directly shows the achievement happened. Do not paraphrase, translate, summarize, or stitch together text from different places. Results whose quote cannot be found in the source are discarded automatically.
    • confidence — one of "high", "medium", "low":
        • "high": the source explicitly reports the completed achievement with specifics that fill most fields for its indicator.
        • "medium": the source explicitly reports the completed achievement, but some key details are missing.
        • "low": the achievement is implied, planned, partial, or only mentioned. Low-confidence results are discarded — prefer omitting them.
    • stated_fields and inferred_fields — together, list EVERY MDS field you filled for the result, each in exactly one of the two arrays:
        • Count these fields when you fill them: lead_center, geo_focus, contributing_center, contributing_partners, evidence, and each field inside the type-specific block written as "<block>.<field>" (e.g., "capacity_sharing.number_people_trained", "policy_change.policy_stage", "innovation_development.innovation_readiness_level"). Do not list title, description, supporting_quote, or confidence.
        • stated_fields: the source explicitly states the value (the number, name, place, date, or stage is written in the source).
        • inferred_fields: you derived, estimated, classified, or assumed the value because the source does not state it.
        • Be honest: a classification the source does not state (for example, a readiness level or policy stage you judged yourself) is inferred. Results whose fields are mostly inferred are discarded automatically — prefer omitting an inferred field over guessing it.
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
Your output must be a single valid JSON object with a results array, and must not include any additional text, comments, footnotes, or explanations outside the JSON fields defined here.

Required and mandatory fields:
• indicator
• title
• description
• geo_focus
• supporting_quote
• confidence
• stated_fields
• inferred_fields

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
            "evidence": [{"link": "https://...", "description": "<string>"}],
            "supporting_quote": "<verbatim passage copied from the source>",
            "confidence": "<high | medium | low>",
            "stated_fields": ["<field the source states explicitly>", "..."],
            "inferred_fields": ["<field you inferred>", "..."]
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
