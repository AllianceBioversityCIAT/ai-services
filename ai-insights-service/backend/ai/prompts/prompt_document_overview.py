DEFAULT_PROMPT_DOCUMENT_OVERVIEW = """
## TASK:
Synthesize all the context provided above (project information, project results, and uploaded evidence) into a single structured project overview for the SAME project.

================================================================================

## OUTPUT FORMAT:
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

================================================================================

## GUIDELINES:
- Synthesize information across ALL provided sources — do not produce separate overviews per file.
- Use STAR project information and results metadata to enrich the overview, especially for project context, SDGs, and reported results.
- Use uploaded documents as evidence to support, detail, or complement the STAR metadata.
- Be precise and factual. Do not infer or fabricate information not present in the provided context.
- If a field cannot be determined, use null for string fields or an empty list [] for array fields.
- The project_summary should stand on its own and give the user a clear understanding of the project.
- For key_findings and recommendations, extract actual content from the documents and/or STAR results metadata.
- Avoid mentioning budget, funding amounts, costs, salaries, or other financial figures, and other sensitive information (e.g., personal data, internal disputes, confidential negotiations) anywhere in the response.

Respond ONLY with the JSON object. Do not include any additional text, explanations, or markdown code fences.
"""
