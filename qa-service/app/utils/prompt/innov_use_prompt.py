"""Prompt builder for evaluating Innovation Use Level."""

import json


def build_use_level_prompt(result_metadata: dict, evidence_context: str = "") -> str:
    """
    Build prompt for evaluating innovation use level (scale of use).
    
    Args:
        result_metadata: Full metadata dictionary
        evidence_context: Formatted evidence content (optional)
    
    Returns:
        Formatted prompt string
    """
    prompt = """
You are an AI expert evaluating the **Scale of Use** for CGIAR innovation results.

## Your Task
Reevaluate the **Scale of use** based on the information provided:

- Use refers to the extent to which an innovation is already being used in society, and by whom. It is measured from low use, where innovations are used only by project teams and their direct partners, to high use where innovations are commonly used by independent end-users.
- An innovation that is only used by the project, design or intervention team or its direct partners will score low in innovation use. Innovations that are commonly used by anticipated end-users will score high in innovation use. Users that are directly incentivized by a project or intervention to use an innovation are considered project team or direct partners which will score as low innovation use.

## Scaling Use Calculator

Assign **exactly one** of the following levels (0-9):

• **Level 0: No use** - Innovation is not used.
• **Level 1: Project lead organization** - Innovation is used by organization(s) leading the innovation development.
• **Level 2: Partners** - Innovation is used by some partners involved in initial innovation development.
• **Level 3: Partners** - Innovation is commonly used by partners involved in initial innovation development.
• **Level 4: Connected next-user** - Innovation is used by some organizations connected to partners involved in the initial innovation development.
• **Level 5: Connected next-user** - Innovation is commonly used by organizations connected to partners involved in the initial innovation development.
• **Level 6: Unconnected next-user** - Innovation is used by organizations not connected to partners involved in the initial innovation development.
• **Level 7: Unconnected next-user** - Innovation is commonly used by organizations not connected to partners involved in the initial innovation development.
• **Level 8: End-user / Beneficiaries** - Innovation is used by some end-users or beneficiaries who were not involved in the initial innovation development.
• **Level 9: End-user / Beneficiaries** - Innovation is commonly used by end-users or beneficiaries who were not involved in the initial innovation development.

## Important Notes

- Must be defined as a number between 0 and 9. Just use the number, not the description.
- If the context provides a specific use level, use that value.
- If the context provides a description of the use level, map it to the corresponding number based on the Scaling Use Calculator.
- If the context provides multiple use levels, use the highest level mentioned. For example, if it is level 4 in Kenya, level 2 in Peru and level 5 in India, only the highest score for the generic rank is retained.
"""
    
    # Add context
    context = json.dumps(result_metadata, indent=2, ensure_ascii=False)
    prompt += f"\n## Context\n\n### Result Metadata\nUse this metadata as the foundation for your evaluation:\n```json\n{context}\n```\n"
    
    # Add evidence context if available
    if evidence_context:
        prompt += f"\n### Evidence Sources\nUse the following evidence to determine the scale of use:\n\n{evidence_context}\n\n**Important**: Base your use level assessment on the actual adoption, usage patterns, and end-user information described in the evidence. Look for specific numbers of users, geographic spread, and independence from project teams.\n"
    
    # Add output instructions
    output_instruction = """
## Output
Do not:
• Add text before or after the JSON.
• Add any explanatory sentences, notes, or references.
• Include markdown code blocks like ```json or ```.
• Escape quotes unless necessary.
• Wrap the JSON in additional quotes or strings.

The response must be raw JSON only — nothing else.
Follow this exact structure:

{
    "use_level": "0-9"
}

- The `use_level` value must be a **number only** (as a string): "0" through "9".
- Do **not** add any extra text outside the JSON.
"""
    
    prompt += output_instruction
    
    return prompt