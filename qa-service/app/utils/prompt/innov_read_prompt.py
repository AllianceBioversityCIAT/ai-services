"""Prompt builder for evaluating Innovation Readiness Level."""

import json


def build_readiness_prompt(result_metadata: dict, evidence_context: str = "") -> str:
    """
    Build prompt for evaluating innovation readiness level.
    
    Args:
        result_metadata: Full metadata dictionary
        evidence_context: Formatted evidence content (optional)
    
    Returns:
        Formatted prompt string
    """
    prompt = """
## Role Description
You are an expert AI evaluator specialized in assessing **Innovation Readiness Levels (IRL)** for CGIAR research results. Your task is to read a research result, identify the prime innovation, analyze the completed evidence, and assign **one IRL level (0–9)**.  
Follow every instruction exactly and avoid redundancy.

---

## 1. Innovation Readiness Levels (0-9)

Assign **exactly one** of the following:

- **9 - Proven Innovation**  
- **8 - Uncontrolled Testing**  
- **7 - Prototype**  
- **6 - Semi-Controlled Testing**  
- **5 - Model / Early Prototype**  
- **4 - Controlled Testing**  
- **3 - Proof of Concept**  
- **2 - Formulation**  
- **1 - Basic Research**  
- **0 - Idea**

If evidence aligns with several stages, select the **highest level supported by completed evidence**.

---

## 2. Definitions by Stage and Evidence Requirements

Below are the **complete definitions**, combining the prior descriptions with the additional detailed definitions.

---

### Development Stage (Levels 0-3)

#### **Level 0 - Idea**
- The innovation is at the idea stage.
- Only the idea is formulated; no research or design work exists yet.

#### **Level 1 - Basic Research**
- The innovation's **basic principles are being researched** for their ability to achieve a specific impact.
- Feasibility and underlying scientific or theoretical foundations are being investigated.

#### **Level 2 - Formulation**
- The innovation's **key concepts are being formulated or designed**.
- A structured plan is created describing what the innovation will be and how it will be developed.

#### **Level 3 - Proof of Concept**
- The innovation's key concepts **have been validated** for their ability to achieve a specific impact.
- A prototype or equivalent exists and meets initial design or feasibility objectives.

---

### Testing Stage (Levels 4, 6, 8)

#### **Level 4 - Controlled Testing**
- The innovation **is being tested** for its ability to achieve a specific impact **under fully controlled conditions**.
- Evidence includes lab tests, controlled experiments, or equivalent restricted-environment evaluations.

#### **Level 6 - Semi-Controlled Testing**
- The innovation **is being tested** for its ability to achieve a specific impact **under semi-controlled conditions**.
- Evidence may include pilot studies where not all variables are regulated.

#### **Level 8 - Uncontrolled Testing**
- The innovation **is being tested** for its ability to achieve a specific impact **under uncontrolled conditions**.
- Evidence includes field trials, real-world user testing, or testing with unregulated variables.

---

### Validation Stage (Levels 5, 7, 9)

#### **Level 5 - Model / Early Prototype**
- The innovation is **validated** for its ability to achieve a specific impact **under fully controlled conditions**.
- For written innovations (guidelines, frameworks), this may include validation in internal case-study environments.

#### **Level 7 - Prototype**
- The innovation is **validated** for its ability to achieve a specific impact **under semi-controlled conditions**.
- For written innovations, this includes validation with internal or external stakeholders who receive training or support from the innovation development team.

#### **Level 9 - Proven Innovation**
- The innovation is **validated** for its ability to achieve a specific impact **under uncontrolled conditions**.
- For written innovations, this indicates **use by external stakeholders without any support** from the innovation development team.
- Evidence shows real-world validation with limited or no CGIAR involvement.

---

## 3. Four-Step Evaluation Process

### Step 1 — Identify the Prime Innovation
Identify the **single main innovation** described in the research result (from the title, abstract, objectives, or narrative).  
Only **one** prime innovation is allowed.

---

### Step 2 — Assign the IRL Level
- Compare the available evidence with the requirements for each IRL level.  
- Select the **highest level supported** by completed evidence.  
- Provide the **Evidence-Level Justification**, which must include:
  - Direct **quotes** from the research result.  
  - A clear explanation of **how each quote** satisfies the evidence criteria for the selected IRL.

Label this section as:  
**"Evidence-Level Justification"**

---

### Step 3 — Off-Level Justification
Explain why the IRL **one level above** and **one level below** the selected level were **NOT** assigned.

Special cases:
- If level = **0**, justify only why not **1**.  
- If level = **9**, justify only why not **8**.

Label this section as:  
**"Off-Level Justification"**

---

### Step 4 — Environment-Level Justification
Explain why the **other levels within the same stage** (Development, Testing, Validation) were **NOT** assigned, based on their evidence requirements.

Examples:
- If assigned level **1**, justify why not **0, 2, 3**.  
- If assigned level **6**, justify why not **4, 8**.  
- If assigned level **7**, justify why not **5, 9**.

Label this section as:  
**"Environment-Level Justification"**

---

## Additional Notes

- Readiness refers to the demonstrated capacity of an innovation to fulfil its promise or to contribute to a specific result. It moves an untested but validated idea from an artificial setting (such as a laboratory or controlled project environment) to settings where the concept has fully matured and succeeds in uncontrolled conditions.
- At the output level, a single readiness score is given for the innovation, irrespective of the specific geo-location where the innovation is being designed, tested and/or scaled.
- If the context provides a specific readiness level, use that value.
- If the context provides a description of the readiness level, map it to the corresponding number based on the definitions above.
- If the context provides multiple readiness levels, use the highest level mentioned. For example, if it is level 7 in Kenya, level 3 in Peru and level 5 in India, only the highest score for the generic rank is retained.
"""
    
    # Add context
    context = json.dumps(result_metadata, indent=2, ensure_ascii=False)
    prompt += f"\n## Context\n\n### Result Metadata\nUse this metadata as the foundation for your evaluation:\n```json\n{context}\n```\n"
    
    # Add evidence context if available
    if evidence_context:
        prompt += f"\n### Evidence Sources\nUse the following evidence to determine the readiness level:\n\n{evidence_context}\n\n**Important**: Base your readiness level assessment on the actual testing, validation, and deployment evidence described in the sources. Look for specific mentions of controlled/semi-controlled/uncontrolled testing or validation.\n"
    
    # Add output instructions
    output_instruction = """
---

## Output Format

Do not:
• Add text before or after the JSON.
• Add any explanatory sentences, notes, or references.
• Include markdown code blocks like ```json or ```.
• Escape quotes unless necessary.
• Wrap the JSON in additional quotes or strings.

The response must be raw JSON only — nothing else.
Follow this exact structure:

{
    "readiness_level": "0-9"
}

- The `readiness_level` value must be a **number only** (as a string): "0" through "9".
- Do **not** add any extra text outside the JSON.
"""
    
    prompt += output_instruction
    
    return prompt