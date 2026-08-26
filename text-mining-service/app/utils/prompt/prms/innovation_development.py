INNOVATION_DEVELOPMENT_SECTION = """
⸻

Additional Requirements for "Innovation Development"

Indicator definition:
    • Refers to a new, improved, or adapted output or groups of outputs such as technologies, products and services, policies, and other organizational and institutional arrangements with high potential to contribute to positive impacts when used at scale (MELCoP Glossary).
    • In PRMS this is an Output — it tracks the development of research ideas into proven innovations and profiles innovations as they progress along the development pathway.
    • Purpose in reporting: profile Alliance/CGIAR innovations and monitor progress from idea through validation under increasingly realistic conditions.

Type-specific block: innovation_development (object, required for this indicator when type-specific data exists)

innovation_typology (object inside innovation_development)
    • Return code and name together. The name must match exactly one of the catalog names below — do not include the definition in the name field.
    • Use the definitions below to choose the correct typology from the sources:
        • code 12, name "Technological innovation" — Innovations of technical/ material nature, including varieties/ breeds; crop and livestock management practices; machines; processing technologies; big data and information systems.
        • code 13, name "Capacity development innovation" — Innovations that strengthen capacity, including farmer, extension or investor decision-support services; accelerator/ incubator programs; manuals, training programs and curricula; online courses.
        • code 14, name "Policy, organizational or institutional innovation" — Innovations that create enabling conditions, including policy, legal and regulatory frameworks; business models; finance mechanisms; partnership models; public/ private delivery strategies.
        • code 15, name "Other/I’m not sure/This typology does not work for my innovation" — Unknown or the type does not work for the innovation.
    • Omit innovation_typology if the typology cannot be determined from sources.

innovation_developers (string inside innovation_development)
    • The innovation developer is the first author of the Innovation Profile document and the primary contact for the innovation.
    • When available in sources, extract first name, family name, email address, and/or organizational affiliation for each developer or contact person.
    • None of these details is required on its own — include whatever the sources support (e.g., only a name, only an email, or name plus affiliation).
    • Return a single string. For each person, combine the available details in plain text, separated by commas where helpful (e.g., "John Doe, john.doe@example.org, International Center for Agricultural Research in the Dry Areas").
    • When multiple developers are named, separate each person with a semicolon and space(e.g., "John Doe, ICARDA; Marie Curie, marie.curie@example.org).
    • Do not invent missing details.
    • Omit innovation_developers only if no developer or contact person can be identified at all from sources.

innovation_readiness_level (object inside innovation_development)
    • Return id and name together. The name must match exactly one of the catalog names below — do not include the definition in the name field.
    • Use the definitions below to choose the correct readiness level from the sources.
    • If sources provide multiple readiness levels for different locations, use the highest level mentioned.
    • If sources state only a Scaling Readiness level number (0-9), map to the matching id and name below (level 0 → id 11, level 1 → id 12, … level 9 → id 20).
        • id 11, name "Idea" (level 0) — The innovation is at idea stage.
        • id 12, name "Basic Research" (level 1) — The innovation's basic principles are being researched for their ability to achieve a specific impact.
        • id 13, name "Formulation" (level 2) — The innovation's key concepts are being formulated or designed.
        • id 14, name "Proof of Concept" (level 3) — The innovation's key concepts have been validated for their ability to achieve a specific impact.
        • id 15, name "Controlled Testing" (level 4) — The innovation is being tested for its ability to achieve a specific impact under fully-controlled conditions.
        • id 16, name "Model/Early Prototype" (level 5) — The innovation is validated for its ability to achieve a specific impact under fully controlled conditions.
        • id 17, name "Semi-Controlled Testing" (level 6) — The innovation is being tested for its ability to achieve a specific impact under semi-controlled conditions.
        • id 18, name "Prototype" (level 7) — The innovation is validated for its ability to achieve a specific impact under semi-controlled conditions.
        • id 19, name "Uncontrolled Testing" (level 8) — The innovation is being tested for its ability to achieve a specific impact under uncontrolled conditions.
        • id 20, name "Proven Innovation" (level 9) — The innovation is validated for its ability to achieve a specific impact under uncontrolled conditions.
    • Omit innovation_readiness_level if the readiness level cannot be determined from sources.

Example:
{
    "innovation_development": {
        "innovation_typology": {
            "code": 12,
            "name": "Technological innovation"
        },
        "innovation_developers": "John Doe, john.doe@icarda.org, International Center for Agricultural Research in the Dry Areas",
        "innovation_readiness_level": {
            "id": 14,
            "name": "Proof of Concept"
        }
    }
}
"""
