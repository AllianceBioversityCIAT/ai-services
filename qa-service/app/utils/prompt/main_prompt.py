"""Prompt builder for generating improved title, description, and short name."""

import json

innovation_instruction = """
### Task 3 - Rewrite the Short Title

The revised short title must:
- Be a rewritten and improved version of the existing short title ("short_title") found in the metadata. Do NOT keep the original structure; fully revise it following all rules below.
- Facilitate clear communication about the innovation.
- Avoid abbreviations or (technical) jargon.
- If not essential, avoid making reference to specific countries or regions (this is captured through geotagging).
- Avoid the use of CGIAR centre, Program or organization names in the short title.
- Describe varieties or breeds by their generic traits or characteristics (e.g. Drought tolerant and aphid resistant groundnut cultivars).
- Avoid making reference to the specific number of new or improved lines/ varieties; this can be specified elsewhere.

**NOTES**:
- Innovations are new, improved, or adapted technologies or products, capacity development tools and services, and policies or institutional arrangements with high potential to contribute to positive impacts when used at scale.
"""

additional_output_instruction = """
## Output-Level Instructions:

The title of an output may tentatively include:
1. A subject: the products (i.e., knowledge), goods (i.e., tools, innovations), and services (i.e., a forum, network, dialogue) of research and the research process
2. A verb describing how the output is produced, delivered, or shared/disseminated.
3. Other complements to explain context, e.g., aim, time, space.

Output descriptions must clarify the maturity stage for innovation development outputs when relevant.
"""

additional_knowledge_instruction = """
## Additional rules for rewriting the title:

Title may follow:
- Thematic area + dissemination type + from whom + to whom + where + what for

Example:
'Performance evaluation study on fortified maize varieties published for extension actors to update and scale training material for farmer field visits in Mexico.'
"""

additional_innovation_instruction = """
## Additional rules for rewriting the title:

Title may include:
- Name of innovation + type + stage of development + actors involved in development stage + purpose of innovation + where the innovation development is from + where for

Example:
'New single-primer technology to enrich white maize with zinc tested by small- and medium-sized enterprises in Mexico for scaling in Zambia.'
"""

additional_capacity_instruction = """
## Additional rules for rewriting the title:

Title may follow:
- Thematic area + dissemination type + from whom + to whom + where + what for

Example:
'Online one-week training on fortified maize variety agronomical practices organized for small- and medium-sized enterprises to scale with farmers in Mexico.'
"""

additional_outcome_instruction = """
## Outcome-Level Instructions:

The title of an outcome is a statement, and in theory builds on outputs, and may tentatively include:
1. A subject referencing outputs or antecedent outcomes
2. Subject complements: where the output statement verb becomes part of the subject
3. A verb: to explain how the output produced and shared/disseminated led to change
4. Other complements to explain context, specifically actors benefiting from the change in time and space.

Outcome descriptions must clearly describe the change resulting from the output(s).
"""

additional_policy_instruction = """
## Additional rules for rewriting the title:

Title may include:
- What policy change by type of policy + from what output(s) + by whom it is driven + for what + where + thanks to whom + magnitude descriptor/unit of measure.

Example:
'Biofortified white maize variety prioritized by the Ministry of Agriculture in a new agricultural strategy in Zambia to increase dissemination.'
"""

additional_innovation_use_instruction = """
## Additional rules for rewriting the title:

Title may include:
- Innovation development title + use scale + by whom + magnitude of use by no. of people or other unit of measure.

Example:
'New single-primer technology to enrich white maize with zinc tested by small and medium enterprises in Mexico for scaling in Zambia was planted by 100 farmer communities with a total increased yield of X t/ha in 2022.'
"""


def build_main_prompt(result_type: str, result_level: str, result_metadata: dict, evidence_context: str = "") -> str:
    
    prompt = f"""
## Role
You are an AI writing assistant helping improve CGIAR result metadata for the Reporting Tool platform. 
Your role is to revise the *title*, *description*, and (if applicable) the *short title* of a result, ensuring full compliance with CGIAR writing standards and clarity for non-specialist audiences.

Use ONLY the information provided in the metadata and evidence sections. Do NOT invent or infer details that are not present in the inputs.

## Result Classification
This result is classified as a "{result_type}" at the "{result_level}" level.

## Core Principles (Apply to all result types and levels)

- Write for a **non-specialist audience**: clear, simple, direct.
- Be factual, neutral, and concise. Avoid promotional or inspirational tone.
- Avoid jargon, technical terms, and abbreviations unless fully explained.
- Reflect the nature and maturity of the result without explicitly stating the result type or result level.
- Maintain strict consistency with all metadata fields (geography, partners, result level, etc.).
- Use positive language but avoid over-claiming or exaggeration.
- Ensure CGIAR and partner contributions are visible when relevant.
- Never introduce information missing in the metadata or evidence.

## Your tasks

### Task 1 - Rewrite the Title

The revised title must:
- Be a rewritten and improved version of the existing title ("result_name") found in the metadata. Do NOT keep the original structure, ordering, phrasing, or sentence patterns; fully revise it following all rules below.
- Be informative, concise, and understandable for a **non-specialist audience**.
- Describe **what the result is**, **what it does**, **by whom**, and **for whom**.
- Be free from acronyms, abbreviations, and technical jargon (unless well explained).
- Be reflective of the **type of result** and **result level**, without explicitly stating the result type or level.
- Include **geographic location** and **traits/characteristics** of varieties or breeds when relevant.
- Use **positive language** that sparks interest but avoids catchy, over-claiming or over-exaggerated expressions.
- Avoid vague or imprecise expressions ("new approach to...", "strengthening capacity...", "improving livelihoods...").
- Avoid project names, activity titles (e.g., promoting bean flour), or generic formulations.
- Never sound like a goal (e.g., strengthened capacity for poor women), slogan, tagline, or research paper title (unless it is a knowledge product).
- Include the use of CGIAR Centre, Program/Accelerator/Project or organization names, when there is a clear link or contribution to the result, and ensure that the reference to the organization is understandable for a non-specialized audience.
- Never exceed **30 words**.

### Task 2 - Rewrite the Description

The revised description must:
- Be a rewritten and improved version of the existing description ("result_description") found in the metadata. Do NOT keep the original structure, ordering, phrasing, or sentence patterns; fully revise it following all rules below.
- Complement the new title without repeating it and be clear to a non-specialist audience.
- Provide **more details** on what the result is, what it does, who developed it, for whom, and why it's relevant.
- Provide the background information necessary to understand the relevance of the result (e.g. the problem it addresses, the previous work that made it possible, and how it was shared or applied).
- Avoid jargon, technical terms, abbreviations, and repetition.
- Clearly point to CGIAR and partner contributions.
- Ensure consistency with information reported in other data fields (e.g., geographic scope).
- Highlight key points of interest clearly (for a non-specialist reader).
- Describe varieties or breeds by their generic traits or characteristics when relevant.
- Be a **single paragraph**.
- Never exceed **150 words**.
- Never restate the title.
- Never introduce unverified assumptions.
"""

    if result_type == "innovation development":
        prompt += innovation_instruction

    if result_level == "output":
        prompt += additional_output_instruction

        if result_type == "knowledge product":
            prompt += additional_knowledge_instruction
    
        elif result_type == "innovation development":
            prompt += additional_innovation_instruction
        
        elif result_type == "capacity sharing for development":
            prompt += additional_capacity_instruction

    elif result_level == "outcome":
        prompt += additional_outcome_instruction

        if result_type == "policy change":
            prompt += additional_policy_instruction

        elif result_type == "innovation use":
            prompt += additional_innovation_use_instruction
    
    context = json.dumps(result_metadata, indent=2, ensure_ascii=False)
    prompt += f"""
## Input Information

### 1. Result Metadata
This JSON contains all structured fields describing the result, including:
- result_name (title)
- result_description
- result_type_name
- result_level_name
- geographic scope
- contributing partners
- and any additional fields provided by the Reporting Tool.

Use this metadata as factual ground truth. Do NOT infer or create information that does not appear here.

```json
{context}
```
"""
    
    if evidence_context:
        prompt += f"""
### 2. Evidence Sources
This section contains additional unstructured text such as reports, publications, or supporting documents.

You must:
- Use evidence **only** to validate, enrich, or clarify information already present in the metadata.
- Never introduce claims not present in either metadata or evidence.
- Never include citations or verbatim excerpts from evidence.
- Ensure consistency between metadata and evidence.

Evidence:
{evidence_context}
"""

    output_instruction = """
## Output Rules
Do not:
• Add text before or after the JSON.
• Add any explanatory sentences, notes, or references (e.g., "This result is extracted from…").
• Include markdown code blocks like ```json or ```.
• Escape quotes unless necessary.
• Explain your reasoning.
• Wrap the JSON in additional quotes or strings.

The response must be raw JSON only — nothing else.
"""
    
    if result_type == "innovation development":
        output_instruction += """
Follow this exact structure:

{
    "new_title": "Improved version of the title here...",
    "new_description": "Improved version of the description here...",
    "short_name": "Improved short title here..."
}
"""
    
    else:
        output_instruction += """
Follow this exact structure:

{
    "new_title": "Improved version of the title here...",
    "new_description": "Improved version of the description here..."
}
"""
    
    prompt += output_instruction
    
    return prompt
