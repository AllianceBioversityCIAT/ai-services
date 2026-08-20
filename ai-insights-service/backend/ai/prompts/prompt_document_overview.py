"""Default prompt sections for the project overview.

The prompt is split into the four sections exposed by the STAR Prompt Manager:
system_role, context, user_instructions and expected_output_format.

The `context` section is a template: the `{variable}` placeholders are replaced at
generation time with the context actually available for the request. They are shown
read-only in the Prompt Manager so editors can see where the context lands.

These constants are the source of truth for the *default* prompt. A user-modified
version lives in S3 and overrides them, falling back here whenever it is missing.
"""

_SEPARATOR = "=" * 80

DEFAULT_SYSTEM_ROLE = f"""## ROLE:
You are an expert analyst specializing in research, development, and policy projects.

{_SEPARATOR}"""


# NOT an f-string: the {variable} placeholders below must survive to render time.
DEFAULT_CONTEXT = """## CONTEXT YOU WILL RECEIVE:
You will receive context from the following source(s), all belonging to the SAME project:
{available_context_sources}

Review all of the following context, then follow the task instructions at the end of this prompt.

-------

### PROJECT INFORMATION:

{project_information}

-------

### PROJECT RESULTS:

{project_results}

-------

### UPLOADED PROJECT EVIDENCE:

{uploaded_evidence}

-------

### USER INPUT:

{user_input}

""" + _SEPARATOR


DEFAULT_USER_INSTRUCTIONS = """## TASK:
Synthesize all the context provided above (project information, project results, and uploaded evidence) into a single structured project overview for the SAME project.

## GUIDELINES:
- Synthesize information across ALL provided sources — do not produce separate overviews per file.
- Use STAR project information and results metadata to enrich the overview, especially for project context, SDGs, and reported results.
- Use uploaded documents as evidence to support, detail, or complement the STAR metadata.
- Be precise and factual. Do not infer or fabricate information not present in the provided context.
- If a field cannot be determined, use null for string fields or an empty list [] for array fields.
- The project_summary should stand on its own and give the user a clear understanding of the project.
- For key_findings and recommendations, extract actual content from the documents and/or STAR results metadata.
- Avoid mentioning budget, funding amounts, costs, salaries, or other financial figures, and other sensitive information (e.g., personal data, internal disputes, confidential negotiations) anywhere in the response."""


DEFAULT_EXPECTED_OUTPUT_FORMAT = """## OUTPUT FORMAT:
Return ONLY a valid JSON object with the following structure:
{
    "project_title": "Project title inferred from the documents, STAR metadata, or the most representative title",
    "project_summary": "A concise 2-4 paragraph executive summary explaining what the project is about, its goals, scope, and main content across all sources. Do NOT mention budget, funding amounts, costs, or other sensitive information (e.g., personal data, internal disputes, confidential negotiations).",
    "documents_analyzed": [
        {
            "file_name": "Name of the file",
            "document_type": "Type of document (e.g., research paper, technical report, policy brief, proposal)",
            "role_in_project": "Brief description of what this document contributes to the project"
        }
    ],
    "key_topics": ["Main topics and themes covered across project documents and results metadata"],
    "key_findings": ["Key findings, results, or conclusions drawn from the documents and STAR results metadata"],
    "objectives": ["Project objectives or goals if mentioned — otherwise an empty list"],
    "authors": ["Authors, contributors, or editors mentioned across documents — otherwise an empty list"],
    "organizations": ["Organizations, institutions, or funders involved — otherwise an empty list"],
    "methodology": "Brief description of methods or approach used, or null if not applicable",
    "recommendations": ["Explicit recommendations or next steps if present — otherwise an empty list"],
    "geographic_scope": "Geographic regions, countries, or global scope covered, or null if not specified",
    "language": "Primary language of the documents (e.g., English, Spanish)"
}

Respond ONLY with the JSON object. Do not include any additional text, explanations, or markdown code fences."""


DEFAULT_PROMPT_DOCUMENT_OVERVIEW = {
    "system_role": DEFAULT_SYSTEM_ROLE,
    "context": DEFAULT_CONTEXT,
    "user_instructions": DEFAULT_USER_INSTRUCTIONS,
    "expected_output_format": DEFAULT_EXPECTED_OUTPUT_FORMAT,
}
