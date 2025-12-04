"""Prompt builder for evaluating Impact Area Scores."""

import json

def build_impact_area_prompt(result_metadata: dict, evidence_context: str = "") -> str:
    prompt = """
You are an AI expert evaluating CGIAR result metadata for Impact Area relevance.

CGIAR (the Consultative Group on International Agricultural Research) is a global partnership focused on research for a food-secure future. The research results you will evaluate come from CGIAR initiatives and projects in agriculture, forestry, fisheries, climate, nutrition, poverty reduction, gender, youth, social inclusion, and environmental sustainability.

Your role is to **re-evaluate the Impact Area scores** for a single CGIAR result, based on its metadata, and assign a score (0, 1, or 2) for each of the five CGIAR Impact Areas:
1. Gender equality, youth and social inclusion
2. Climate adaptation and mitigation
3. Nutrition, health and food security
4. Environmental health and biodiversity
5. Poverty reduction, livelihoods and jobs

Your objective is to assign scores that are **as coherent, consistent, and evidence-based as possible**, strictly following the definitions and criteria below.

--------------------------------------------------
## 1. General Scoring Framework (applies to all Impact Areas)

For **each** of the five Impact Areas, assign exactly one of these scores:

- **0 = NOT TARGETED**
  - The result has been screened against the Impact Area and is **not found to directly contribute** to any aspect of that area as defined in this prompt.
  - Any linkage is **indirect, incidental, or inferred**, not an explicit or stated objective of the result.
  - The result focuses on other topics, and any contribution to this Impact Area is minor, non-deliberate, or not clearly evidenced.

- **1 = SIGNIFICANT**
  - The result **directly and intentionally contributes** to one or more aspects of the Impact Area.
  - The Impact Area is an **important, explicit objective**, but **not the principal or primary objective** of the result.
  - The result has other primary goals, but it has been formulated or adjusted to **also** contribute in a meaningful way to this Impact Area.

- **2 = PRINCIPAL**
  - The Impact Area is the **primary/principal objective** of the result.
  - Contributing to this Impact Area is **fundamental to the design** of the activity leading to the result.
  - The result **would not have been undertaken** without the intention to contribute to one or more aspects of this Impact Area.

### 1.1 Cross-cutting rules

Apply these rules consistently across all Impact Areas:

- **Direct vs indirect contribution**
  - If the contribution is only **indirect, inferred, or incidental**, assign **0 (NOT TARGETED)**.
  - Only **direct and intentional** contributions (explicitly stated objectives, activities, outcomes, or expected impacts) can justify **1 (SIGNIFICANT)** or **2 (PRINCIPAL)**.

- **At least one non-zero score**
  - In most cases, **at least one Impact Area** should receive a score of **1 or 2**.
  - A result with **0 for all five Impact Areas** should be treated as a **rare exception**, used only when there is truly no direct or intentional contribution to any Impact Area.

- **Limit on Principal scores**
  - **No more than two Impact Areas** should receive a score of **2 (PRINCIPAL)**.
  - A result with three or more Impact Areas scored as **2** should be **very rare** and only used when the metadata clearly supports that multiple Impact Areas are truly principal objectives.

- **Do not base scores on donor preferences**
  - Scores must be based on the **relevance of the Impact Area to the result itself**, not on donor interests or how attractive an Impact Area might be to funders.

- **Do not score solely on global targets**
  - The collective global targets are provided as **context and orientation**, but you should score based on the **broader Impact Area definitions and example topics**, not on numeric target matching.

- **Evidence-based scoring**
  - Always ground your scoring in the **information provided in the result metadata** (e.g., title, description, objectives, outcomes, locations, beneficiaries).
  - If the metadata does not provide enough evidence for a direct and intentional contribution, you must lean toward a lower score (0 rather than 1, 1 rather than 2).

--------------------------------------------------
## 2. Impact Area Definitions and Detailed Guidance

In this section, you will find specific definitions, objectives, and examples for each Impact Area. Use them to decide whether the result is NOT TARGETED (0), SIGNIFICANT (1), or PRINCIPAL (2).

For each Impact Area, pay special attention to:
- What counts as a **direct and intentional** contribution.
- What should be considered **out of scope** or only indirectly related.
- How to distinguish between **SIGNIFICANT (1)** and **PRINCIPAL (2)**.

--------------------------------------------------
### 2.1 Gender Equality, Youth and Social Inclusion

**What this Impact Area covers**

Gender equality refers to the equal rights, responsibilities, and opportunities of all individuals regardless of gender. In agriculture and food systems, it addresses disparities and biases in:
- Access to resources (land, finance, technology, inputs, information)
- Decision-making power and leadership
- Distribution of benefits and opportunities

Youth and social inclusion focus on:
- Empowering young people in food, land, and water systems
- Removing socio-political barriers to inclusion
- Addressing the needs and preferences of disadvantaged or marginalized groups

**CGIAR collective targets for this Impact Area include:**
- Closing the gender gap in rights to economic resources and access to ownership and control over land and natural resources for over **500 million women** working in food, land, and water systems.
- Offering rewardable opportunities to **267 million young people** who are not in employment, education, or training.

**Example topics that clearly fall under this Impact Area:**
- Empowering women and youth in agriculture and food systems.
- Encouraging women and youth entrepreneurship.
- Addressing socio-political barriers to social inclusion in food systems.
- Ensuring equal access to productive resources, services, and markets.
- Designing crop, breed, or technology options tailored to the **requirements and preferences of women, youth, or disadvantaged groups**.
- Research on gender dynamics, power relations, decision-making, roles and responsibilities in agriculture and food systems.

**Specific criteria for scoring:**

- **0 = NOT TARGETED**
  - The result does **not** explicitly mention gender equality, youth, or social inclusion as an objective, activity, or outcome.
  - The result does **not** analyze or address gender roles, power dynamics, access differences, or inclusion of disadvantaged groups in a social (not biological) sense.
  - Merely reporting **gender-disaggregated data**, counting male/female participants, or referencing "households" without explicit analysis of gender or youth roles is **not sufficient** for a non-zero score.
  - References to biological sex of animals or plants (e.g., male/female animals, male/female plant traits) are **not** gender equality topics and should not lead to a non-zero score.

- **1 = SIGNIFICANT**
  - The result includes a **direct and explicit** consideration of gender equality, youth, or social inclusion, but these are **secondary objectives**.
  - Examples:
    - A technology trial where the main objective is productivity, but the result includes a substantial analysis of gendered adoption, youth participation, or access differences.
    - A value-chain study focused on markets and competitiveness, which also assesses how benefits and opportunities differ for women, youth, or marginalized groups and draws conclusions relevant for more inclusive policies.
  - The result **generates meaningful insights** about gender/youth/social inclusion (roles, decision-making, access to resources, power dynamics, barriers) that can inform inclusive policies or practices, but the **primary focus** is another area (e.g., productivity, climate, nutrition).

- **2 = PRINCIPAL**
  - The result is **primarily designed** to address gender equality, youth empowerment, or social inclusion.
  - The main objectives explicitly target:
    - Reducing gender disparities in access to land, credit, inputs, or services.
    - Increasing women's or youth's decision-making power, leadership, or control over resources.
    - Overcoming structural barriers faced by marginalized groups in food, land, and water systems.
  - The result would **not exist in its current form** without the intention to contribute to gender equality, youth, or social inclusion as a central purpose.

When this Impact Area receives a score of **2 (PRINCIPAL)**, you must also select the **dominant sub-component**:
- `"Gender equality"`, `"Youth"`, or `"Social Inclusion"`.

--------------------------------------------------
### 2.2 Climate Adaptation and Mitigation

**What this Impact Area covers**

This Impact Area focuses on research that directly addresses:
- **Climate adaptation**: enhancing the resilience and adaptive capacity of food, land, and water systems and their actors (e.g., small-scale producers) to climate variability and change.
- **Climate mitigation**: reducing greenhouse gas (GHG) emissions, enhancing carbon sequestration, and transforming agriculture and forest systems into a net carbon sink.

**CGIAR collective targets for this Impact Area include:**
- Turning agriculture and forest systems into a **net sink for carbon by 2050**.
- Equipping **500 million small-scale producers** to be more climate-resilient by 2030.
- Supporting countries in implementing **National Adaptation Plans (NAPs)** and **Nationally Determined Contributions (NDCs)**, and increasing ambition in climate actions by 2030.

**Example topics clearly aligned with this Impact Area:**
- Generating scientific evidence on the impact of climate change on food, land, and water systems, and vice-versa.
- Developing evidence-based climate solutions and policies (adaptation and/or mitigation).
- Enhancing adaptive capacity of small-scale producers while reducing GHG emissions/carbon footprints.
- Providing affordable, accessible **climate-informed services** (e.g., climate-smart advisories, forecasts).
- Developing **climate-resilient crop varieties and breeds**.
- Securing genetic resources for future climate needs.
- Improving methods for climate modeling, scenarios, and forecasts.

**Important distinction:**
- Do **not** confuse climate adaptation/mitigation with generic environmental management.
- Issues such as water quality, nutrient pollution, land degradation, or biodiversity conservation may fall under **Environmental Health and Biodiversity** unless they are explicitly framed in terms of **climate resilience or GHG mitigation**.

**Specific criteria for scoring:**

- **0 = NOT TARGETED**
  - The result does **not** explicitly aim to improve climate resilience, climate adaptation, or mitigation (e.g., GHG reduction, carbon sequestration).
  - Climate change may be mentioned contextually but is **not** a direct or intentional objective of the result.
  - Environmental topics (water, soils, biodiversity) are addressed **without explicit climate adaptation or mitigation framing**.

- **1 = SIGNIFICANT**
  - The result includes a **direct and meaningful** contribution to climate adaptation or mitigation, but this is **not the primary objective**.
  - Examples:
    - A productivity-focused intervention where climate resilience is explicitly considered and measured, but secondary to yield gains.
    - A policy study whose main focus is governance, but it also directly informs NAPs, NDCs, or climate investment decisions.
  - Climate adaptation/mitigation is an **intentional and explicit** dimension of the design or analysis, but not the main focus.

- **2 = PRINCIPAL**
  - The result is **primarily designed** to achieve climate adaptation and/or mitigation outcomes.
  - The main objectives are explicitly framed around:
    - Reducing GHG emissions or carbon footprints in agriculture/forestry systems.
    - Increasing resilience/adaptive capacity of targeted populations or systems to climate risk.
    - Supporting NAPs, NDCs, and climate policy implementation as the central purpose.
  - Without the climate adaptation/mitigation objective, the research or project would **not have been undertaken** in this form.

When this Impact Area receives a score of **2 (PRINCIPAL)**, you must also select the **dominant sub-component**:
- `"Adaptation"` or `"Mitigation"`.

--------------------------------------------------
### 2.3 Nutrition, Health and Food Security

**What this Impact Area covers**

This Impact Area focuses on the **nutrition, health, and food security of humans** (not animals). It includes:
- Human diets and nutritional status.
- Food security in terms of availability, access, affordability, desirability, and stability.
- Human health outcomes related to food systems, including food safety, zoonotic diseases, and antimicrobial resistance.

**CGIAR collective targets for this Impact Area include:**
- Ending hunger for all and enabling **affordable, healthy diets** for the **3 billion people** who currently lack access to safe and nutritious food.
- Reducing cases of **foodborne illness (600 million annually)** and **zoonotic disease (1 billion annually)** in humans by one third.

**Example topics clearly aligned with this Impact Area:**
- Improving diets, nutrition, and food security (affordability, accessibility, desirability, stability) **for humans**.
- Improving **human health** through food systems interventions.
- Increasing and diversifying the **food supply for humans**.
- Managing zoonotic diseases, food safety, and antimicrobial resistance affecting human health.

**Important note:**
- The focus is on **human** nutrition and health. Work dealing only with animal nutrition or animal health, without a clear human nutrition/health or food security link, should **not** automatically receive a non-zero score.

**Specific criteria for scoring:**

- **0 = NOT TARGETED**
  - The result does **not** directly address human nutrition, human health, or food security.
  - Any mention of food, crops, or livestock is focused on other objectives (e.g., productivity, income, environmental outcomes) without explicit intention to improve human diets, health, or food security.
  - Contributions to nutrition, health, or food security are only **indirect or assumed**, not explicitly stated as objectives or outcomes.

- **1 = SIGNIFICANT**
  - The result has a **direct and intentional** component related to human nutrition, health, or food security, but this is **not the primary objective**.
  - Examples:
    - A value chain or market study whose main emphasis is economic, but which explicitly aims to improve availability or affordability of nutritious foods for specific human populations.
    - An agronomic trial where the primary focus is yield or resilience, but which consciously targets nutrient-dense crops to improve human dietary quality.

- **2 = PRINCIPAL**
  - The result is **primarily designed** to improve human nutrition, human health, or food security.
  - The main objectives explicitly aim to:
    - Improve dietary quality, nutrient intake, or reduce malnutrition.
    - Improve food safety, reduce foodborne illness, or address zoonotic diseases affecting humans.
    - Ensure access to safe, nutritious, and affordable food for specific human groups or populations.
  - Without this nutrition/health/food security objective, the project would **not** exist in its current form.

When this Impact Area receives a score of **2 (PRINCIPAL)**, you must also select the **dominant sub-component**:
- `"Nutrition"`, `"Health"`, or `"Food Security"`.

--------------------------------------------------
### 2.4 Environmental Health and Biodiversity

**What this Impact Area covers**

This Impact Area focuses on **staying within planetary boundaries** and protecting **biodiversity** in food, land, and water systems, including:
- Sustainable management of water, land, soils, nutrients, waste, and pollution.
- Conservation of genetic resources and ecosystems.
- Nature-based, ecosystem-based, and agroecological approaches.

**CGIAR collective targets for this Impact Area include:**
- Staying within planetary and regional environmental boundaries, including:
  - Consumptive water use in food production of **less than 2,500 km³ per year**, with focus on stressed basins.
  - **Zero net deforestation**.
  - Nitrogen application of **90 Tg per year** with increased use efficiency and redistribution towards low-input systems.
  - Phosphorus application of **10 Tg per year**.
- Maintaining the **genetic diversity** of seed varieties, cultivated plants, farmed and domesticated animals, and related wild species, including through well-managed genebanks and conservation areas.

**Example topics clearly aligned with this Impact Area:**
- Supporting actions to stay within planetary boundaries for natural resource use and biodiversity through digital tools and decision-support systems.
- Improving management of water, land, soil, nutrients, waste, and pollution.
- Nature-based, ecosystem-based, or agroecological approaches to production and resource management.
- Conserving biodiversity via:
  - Ex situ facilities (genebanks, community seed banks).
  - In situ conservation areas and landscape-level conservation efforts.
- Breeding approaches that explicitly aim to **reduce environmental footprint**.

**Important distinction:**
- Do **not** include climate adaptation/mitigation objectives here. Those belong under **Climate Adaptation and Mitigation**, even if they also have environmental implications.
- Environmental Health and Biodiversity scoring should focus on planetary boundaries and biodiversity, not on climate goals such as NAPs/NDCs or net carbon sinks.

**Specific criteria for scoring:**

- **0 = NOT TARGETED**
  - The result does **not** directly address environmental sustainability, planetary boundaries, or biodiversity conservation.
  - Any environmental benefits are incidental and not explicitly included as objectives or design criteria.

- **1 = SIGNIFICANT**
  - The result includes a **direct and meaningful** component related to environmental health or biodiversity, but this is **not the primary objective**.
  - Examples:
    - A productivity-focused intervention that includes a deliberate strategy to reduce nutrient runoff, improve soil health, or protect water bodies.
    - A breeding program where the main objective is yield or resilience, but environmental footprint reduction is explicitly considered and measured.

- **2 = PRINCIPAL**
  - The result is **primarily designed** to improve environmental health or conserve biodiversity.
  - The main objectives focus on:
    - Staying within sustainable water, nutrient, or land-use boundaries.
    - Reducing pollution and environmental degradation.
    - Conserving genetic resources, species, or ecosystems.
  - Without this environmental/biodiversity objective, the result would not exist in this form.

When this Impact Area receives a score of **2 (PRINCIPAL)**, you must also select the **dominant sub-component**:
- `"Environmental Health"` or `"Biodiversity"`.

--------------------------------------------------
### 2.5 Poverty Reduction, Livelihoods and Jobs

**What this Impact Area covers**

This Impact Area focuses on **reducing poverty**, improving **livelihoods**, and creating or enhancing **employment opportunities**, especially for rural populations and small-scale producers.

**CGIAR collective targets for this Impact Area include:**
- Lifting at least **500 million people** living in rural areas above the extreme poverty line of **US $1.90 per day (2011 PPP)**.
- Reducing by at least half the proportion of men, women, and children living in poverty in all its dimensions, according to national definitions.

**Example topics clearly aligned with this Impact Area:**
- Improving **social protection** and **employment opportunities** by supporting access to resources and markets.
- Developing solutions for **resilient, income-generating agriculture** for small farmers.
- Reducing poverty through adoption of new varieties, breeds, technologies, or practices that significantly **increase or stabilize incomes**.
- Strengthening rural livelihoods through value chains, off-farm employment, or diversification.

**Specific criteria for scoring:**

- **0 = NOT TARGETED**
  - The result does **not** explicitly address poverty reduction, livelihoods, or jobs.
  - The focus is on other outcomes (e.g., agronomic performance, genetic traits, environmental metrics) without explicit linkage to incomes, employment, or multidimensional poverty.
  - Any poverty or livelihood impact is only **assumed or indirect**, not clearly described as an objective or result.

- **1 = SIGNIFICANT**
  - The result makes a **direct and meaningful** contribution to poverty reduction, livelihoods, or jobs, but this is **not the principal objective**.
  - Examples:
    - A productivity-focused study that explicitly analyzes income effects or livelihood improvements for small-scale farmers, but where income is a secondary dimension.
    - A value-chain intervention where the main objective is improving efficiency, but it also directly aims to enhance job opportunities or household incomes.

- **2 = PRINCIPAL**
  - The result is **primarily designed** to reduce poverty, improve livelihoods, or create/strengthen employment opportunities.
  - The main objectives explicitly aim to:
    - Lift target populations above poverty thresholds.
    - Improve income stability, diversification, or resilience of livelihoods.
    - Create or improve jobs (quality, quantity, security) in food, land, and water systems.
  - Without the poverty/livelihood/jobs objective, the research or project would **not** have been undertaken.

When this Impact Area receives a score of **2 (PRINCIPAL)**, you must also select the **dominant sub-component**:
- `"Poverty Reduction"`, `"Livelihoods"`, or `"Jobs"`.

--------------------------------------------------
"""
    
    context = json.dumps(result_metadata, indent=2, ensure_ascii=False)
    prompt += f"""
## 3. Input: Result Metadata

You will receive the **result metadata** as a JSON object:

```json
{context}
```

This metadata may include, for example:
- Result type, title, and description.
- Objectives and expected outcomes.
- Target populations and geographies.
- Thematic tags or focus areas.
- Any other relevant fields.

You must base your scoring only on the evidence available in this metadata. Do not assume or hallucinate objectives or impacts that are not clearly supported by the provided information.
"""

    if evidence_context:
        prompt += f"""
### Evidence Sources

In addition to the result metadata, you will also receive **evidence sources** related to this result (e.g., reports, publications, datasets, project documents, outcome stories). Use these as **complementary inputs** when assigning Impact Area scores.

The evidence may provide:
- More detailed descriptions of activities, outcomes, and beneficiaries.
- Concrete examples of implementation and results.
- Additional information on impacts, locations, or target groups.

Use the following evidence to inform your impact area scoring:

{evidence_context}

**Important**:
- Treat both the metadata and the evidence as authoritative inputs.
- If the evidence provides more specific or updated information than the metadata, give it appropriate weight.
- Do not infer impacts that are not supported by either the metadata or the evidence.
- Focus on **actual outcomes, beneficiaries, and impacts** described in the evidence when deciding whether contributions are direct/intentional (scores 1-2) or only indirect/incidental (score 0).
"""

    output_instruction = """
--------------------------------------------------

## 4. Output Format (STRICT)

You must output only raw JSON, with no additional text, explanations, or markdown.

Do not:
• Add any text before or after the JSON.
• Add explanatory sentences, notes, or references.
• Include markdown code fences like json or .

Do not:
• Escape quotes unless strictly required by JSON syntax.
• Wrap the JSON as a string or inside another structure.

### 4.1 JSON schema

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

### 4.2 Additional output rules
- All scores must be strings (“0”, “1”, or “2”) to match the expected schema.
- For each Impact Area:
    - If the score is 2 (PRINCIPAL), you must include the corresponding *_component field and choose exactly one allowed value that best reflects the main focus.
    - If the score is 0 or 1, you must omit the corresponding *_component field completely.
- Do not add any extra fields or keys beyond those specified.
- Ensure the JSON is valid and parseable.

Use all of the above guidance to assign the most accurate, consistent, and evidence-based scores possible for this result.
"""
    
    prompt += output_instruction
    
    return prompt