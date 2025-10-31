import json

def build_prompt(result_type, result_level, result_metadata):
    prompt = """
You are an AI writing assistant helping improve CGIAR result metadata for the Reporting Tool platform. Based on the full JSON context provided (including the existing title and description), revise the *title* and *description* to ensure they meet the standards outlined below. 
Also generate a *short name* only if the result is of type "Innovation Development".

## Context
The input is a JSON block that includes fields like: result_name (title), result_description, result_type_name, and other metadata such as geographic scope, contributing partners, and result level.

## Your task
1. Rewrite the **Title** ("result_name") to make it:
    - Informative, concise, and understandable for a **non-specialist audience**.
    - Clear about **what the result is**, **what it does**, **by whom**, and **for whom**.
    - Free from acronyms, abbreviations, and technical jargon (unless well explained).
    - Reflective of the **type of result** (e.g., Capacity Sharing for Development, Knowledge product, Innovation Development, Policy Change, Innovation use, etc.) and **result level** (output, outcome or impact), without explicitly stating the result type or level.
    - Including **geographic location** and **traits/characteristics** of varieties or breeds when relevant.
    - Using **positive language** that sparks interest but avoids catchy, over-claiming or over-exaggerated expressions.
    - Not be phrased generically using a paper (unless it is a knowledge product), activity or project title (e.g., promoting bean flour), or as a goal (e.g., strengthened capacity for poor women), or with vague/imprecise expressions (e.g., new approach to...).
    - Include the use of CGIAR Centre, Program/Accelerator/Project or organization names, when there is a clear link or contribution to the result, and ensure that the reference to the organization is understandable for a non-specialized audience.
    - Not exceed 30 words.

2. Rewrite the **Description** ("result_description") to:
- Complement the new title without repeating it and be clear to a non-specialist audience.
- Provide **more details** on what the result is, what it does, who developed it, for whom, and why it's relevant.
- Provide the background information necessary to understand the relevance of the result (e.g. the problem it addresses, the previous work that made it possible, and how it was shared or applied).
- Avoid jargon, technical terms, abbreviations, and repetition.
- Clearly point to CGIAR and partner contributions.
- Ensure consistency with information reported in other data fields (e.g., geographic scope).
- Highlight key points of interest clearly (for a non-specialist reader).
- Describe varieties or breeds by their generic traits or characteristics when relevant.
- Not exceed 150 words.

"""

    if result_type == "innovation development":
        innovation_instruction = """
**NOTES**:
- Innovations are new, improved, or adapted technologies or products, capacity development tools and services, and policies or institutional arrangements with high potential to contribute to positive impacts when used at scale.
- Innovations may be at early stages of readiness (ideation and upstream research) or at more mature stages of readiness (delivery and scaling). 

3. Rewrite the result **Short title** ("short_title") to:
- Try to develop a short name that facilitates clear communication about the innovation.
- Avoid abbreviations or (technical) jargon.
- If not essential, avoid making reference to specific countries or regions (this is captured through geotagging).
- Avoid the use of CGIAR centre, Program or organization names in the short title.
- Varieties or breeds should be described by their generic traits or characteristics (e.g. Drought tolerant and aphid resistant groundnut cultivars).
- The specific number of new or improved lines/ varieties can be specified elsewhere.

"""
        prompt += innovation_instruction

    if result_level == "output":
        additional_level_instruction = """
## Additional instructions for results at the Output level:
The title of an output may tentatively include:
    1. A subject: the products (i.e., knowledge), goods (i.e., tools, innovations), and services (i.e., a forum, network, dialogue) of research and the research process
    2. A verb: to explain how the output is produced and shared/disseminated, with clear reference to maturity levels for innovation development
    3. Other complements to explain context, e.g., aim, time, space.

"""
        prompt += additional_level_instruction

        if result_type == "knowledge product":
            additional_knowledge_instruction = """
## Additional instructions for Knowledge Product result type:
The title can include, for example:
- Thematic area + dissemination type + from whom + to whom + where + what for
e.g., Performance evaluation study on fortified maize varieties published for extension actors to update and scale training material for farmer field visits in Mexico.

"""
            prompt += additional_knowledge_instruction
    
        elif result_type == "innovation development":
            additional_innovation_instruction = """
## Additional instructions for Innovation Development result type:
The title can include, for example:
- Name of innovation + type + stage of development + actors involved in development stage + purpose of innovation + where the innovation development is from + where for
e.g., New single-primer technology to enrich white maize with zinc tested by small- and medium-sized enterprises in Mexico for scaling in Zambia.

"""
            prompt += additional_innovation_instruction
        
        elif result_type == "capacity sharing for development":
            additional_capacity_instruction = """
## Additional instructions for Capacity Sharing for Development result type:
The title can include, for example:
- Thematic area + dissemination type + from whom + to whom + where + what for
e.g., Online one-week training on fortified maize variety agronomical practices organized for small- and medium-sized enterprises to scale with farmers in Mexico.

"""
            prompt += additional_capacity_instruction

    elif result_level == "outcome":
        additional_level_instruction = """
## Additional instructions for results at the Outcome level:
The title of an outcome is a statement, and in theory builds on outputs, and may tentatively include:
    1. A subject: the output or antecedent outcomes
    2. Subject complements: where the output statement verb becomes part of the subject
    3. A verb: to explain how the output produced and shared/disseminated led to change
    4. Other complements to explain context, specifically actors benefiting from the change in time and space.

        """
        prompt += additional_level_instruction

        if result_type == "policy change":
            additional_policy_instruction = """
## Additional instructions for Policy Change result type:
The title can include, for example:
- What policy change by type of policy + from what output(s) + by whom it is driven + for what + where + thanks to whom + magnitude descriptor/unit of measure.
e.g., Biofortified white maize variety prioritized by the Ministry of Agriculture in a new agricultural strategy in Zambia to increase dissemination.

"""
            prompt += additional_policy_instruction

        elif result_type == "innovation use":
            additional_innovation_use_instruction = """
## Additional instructions for Innovation Use result type:
The title can include, for example:
- Innovation development title + use scale + by whom + magnitude of use by no. of people or other unit of measure.
e.g., New single-primer technology to enrich white maize with zinc tested by small and medium enterprises in Mexico for scaling in Zambia was planted by 100 farmer communities with a total increased yield of X t/ha in 2022.

"""
            prompt += additional_innovation_use_instruction
    
    context = json.dumps(result_metadata, indent=2, ensure_ascii=False)
    prompt += f"## Result metadata context (to base your suggestions on):\n```json\n{context}\n```\n"
    
    output_instruction = """
## Output
Return your response in the following JSON format:

```json
{{
"new_title": "Improved version of the title here...",
"new_description": "Improved version of the description here...",
"short_name": "Optional improved short title here (only for Innovation Development, otherwise omit this field)"
}}
"""
    
    prompt += output_instruction
    
    return prompt