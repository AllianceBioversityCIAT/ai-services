"""Prompt builder for evaluating Impact Area Scores."""

import json


def build_impact_area_prompt(result_metadata: dict, evidence_context: str = "") -> str:
    """
    Build prompt for evaluating impact area scores.
    
    Args:
        result_metadata: Full metadata dictionary
        evidence_context: Formatted evidence content (optional)
    
    Returns:
        Formatted prompt string
    """
    prompt = """
You are an AI expert evaluating CGIAR result metadata for Impact Area relevance.

## Your Task
Reevaluate the Impact Area Scores:
    
Provide a score (0, 1 or 2) indicating the relevance of the result for each of the 5 Impact Areas (IAs). IA scores are defined as follows:

0 = Not targeted: The result has been screened against the IA but it has not been found to directly contribute to any aspect of the IA as it is outlined in the CGIAR 2030 Research and Innovation Strategy.
1 = Significant: The result directly contributes to one or more aspects of the IA. However, contributing to the IA is not the principal objective of the result.
2 = Principal: Contributing to one or more aspects of the IA is the principal objective of the result. The IA is fundamental to the design of the activity leading to the result; the activity would not have been undertaken without this objective.

Notes:
- Every result should have at least one score of 1 or 2. Results with scores of 0 for all IAs should be rare cases.
- No more than two IAs should receive scores of 2 for a given result. Results with three IAs with scores of 2 should be rare cases.
- Scores should not be assigned solely based on relevance to the collective global targets, but rather to the IA as more broadly defined in the 2030 Strategy and by the IA Platforms, indicated below.
- Scoring should be based on the relevance of the IAs to a given result and not on other criteria such as a specific donor's level of interest in an IA.

Here is a brief overview of each Impact Area to guide your scoring:

- Gender equality, youth and social inclusion:
    Example topics: Empowering women and youth, encouraging women and youth entrepreneurship, and addressing socio-political barriers to social inclusion in food systems; ensuring equal access to resources; and meeting the specific crop and breed requirements and preferences of women, youth, and disadvantaged groups.
    Collective global targets:
        - To close the gender gap in rights to economic resources, access to ownership and control over land and natural resources for over 500 million women who work in food, land and water systems.
        - To offer rewardable opportunities to 267 million young people who are not in employment, education or training.

- Climate adaptation and mitigation
    Example topics: Generating scientific evidence on the impact of climate change on food, land and water systems, and vice-versa; developing evidence-based solutions that support climate action, including via policies, institutions and finance; enhancing adaptive capacity of small-scale producers while reducing GHG emissions/carbon footprints; providing affordable, accessible climate-informed services; developing climate-resilient crop varieties and breeds; securing genetic resources for future climate needs; and improving methods (e.g. for modeling, forecasts).
    Collective global targets:
        - Turn agriculture and forest systems into a net sink for carbon by 2050.
        - Equip 500 million small-scale producers to be more resilient by 2030.
        - Support countries in implementing National Adaptation Plans and Nationally Determined Contributions, and increased ambition in climate actions by 2030. education or training.

- Nutrition, health and food security
    Example topics: Improving diets, nutrition, and food security (affordability, accessibility, desirability, stability); human health; and managing zoonotic diseases, food safety, and anti-microbial resistance.
    Collective global targets:
        - To end hunger for all and enable affordable, healthy diets for the 3 billion people who do not currently have access to safe and nutritious food.
        - To reduce cases of foodborne illness (600 million annually) and zoonotic disease (1 billion annually) by one third.

- Environmental health and biodiversity
    Example topics: Supporting actions to stay within planetary boundaries for natural resource use and biodiversity through digital tools; improving management of water, land, soil, nutrients, waste, and pollution, including through nature-based, ecosystem-based, and agroecological approaches; conserving biodiversity through ex situ facilities (e.g. genebanks, community seed-banks) or in situ conservation areas; and breeding to reduce environmental footprint.
    Collective global targets:
        - Stay within planetary and regional environmental boundaries: consumptive water use in food production of less than 2,500 km3 per year (with a focus on the most stressed basins), zero net deforestation, nitrogen application of 90 Tg per year (with a redistribution towards low-input farming systems) and increased use efficiency; and phosphorus application of 10 Tg per year.
        - Maintain the genetic diversity of seed varieties, cultivated plants and farmed and domesticated animals and their related wild species, including through soundly managed genebanks at the national, regional, and international levels.

- Poverty reduction, livelihoods and jobs
    Example topics: Improving social protection and employment opportunities by supporting access to resources and markets; developing solutions for resilient, income-generating agriculture for small farmers; and reducing poverty through adoption of new varieties and breeds with better yields.
    Collective global targets:
        - Lift at least 500 million people living in rural areas above the extreme poverty line of US $1.90 per day (2011 PPP).
        - Reduce by at least half the proportion of men, women and children of all ages living in poverty in all its dimensions, according to national definitions.
"""
    
    # Add context
    context = json.dumps(result_metadata, indent=2, ensure_ascii=False)
    prompt += f"\n## Context\n\n### Result Metadata\nUse this metadata as the foundation for your evaluation:\n```json\n{context}\n```\n"
    
    # Add evidence context if available
    if evidence_context:
        prompt += f"\n### Evidence Sources\nUse the following evidence to inform your impact area scoring:\n\n{evidence_context}\n\n**Important**: Consider the actual outcomes, beneficiaries, and impacts described in the evidence when assigning scores.\n"
    
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
    "impact_area_scores": {
        "social_inclusion": "0, 1, or 2",
        "social_inclusion_component": "Gender equality, Youth, or Social Inclusion" (only if social_inclusion score is 2; otherwise omit this field),
        "climate_adaptation": "0, 1, or 2",
        "climate_adaptation_component": "Adaptation or Mitigation" (only if climate_adaptation score is 2; otherwise omit this field),
        "food_security": "0, 1, or 2",
        "food_security_component": "Nutrition, Health, or Food Security" (only if food_security score is 2; otherwise omit this field),
        "environmental_health": "0, 1, or 2",
        "environmental_health_component": "Environmental Health or Biodiversity" (only if environmental_health score is 2; otherwise omit this field),
        "poverty_reduction": "0, 1, or 2",
        "poverty_reduction_component": "Poverty Reduction, Livelihoods, or Jobs" (only if poverty_reduction score is 2; otherwise omit this field)
    }
}
"""
    
    prompt += output_instruction
    
    return prompt