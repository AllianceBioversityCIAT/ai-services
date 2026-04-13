def generate_search_prompt(selected_indicator, selected_year):
  return f"""
Annual report evidence for AICCRA indicator {selected_indicator}, year {selected_year}.
Cluster contributions, milestone achievements, beneficiaries, deliverables, dissemination outputs,
climate-smart agriculture outcomes, climate information services, innovations, tools, capacity building,
Outcome Impact Case Reports, policy influence, and project results across AICCRA clusters:
Ghana, Mali, Senegal, Ethiopia, Kenya, Zambia, Western Africa, Eastern and Southern Africa,
Theme 1, Theme 2, Theme 3, Theme 4.
"""


def generate_summary_prompt(indicator, year, total_expected, total_achieved, progress):
  return f"""
# CONTEXT
AICCRA (Accelerating Impacts of CGIAR Climate Research for Africa) is a multi-country initiative led by CGIAR. Its mission is to scale the impact of climate-smart agriculture, climate information services, and innovative practices to improve resilience, livelihoods, 
and food systems across Africa. The initiative is structured around thematic and country-based clusters, each contributing to a set of key performance indicators.

## What is a Cluster? 
A cluster is defined as the group of AICCRA main activities led by each AICCRA Country Leader (Ghana, Mali, Senegal, Ethiopia, Kenya and Zambia), AICCRA Regional Leaders (Western Africa and Eastern & Southern Africa), and AICCRA Thematic leaders (Theme 1, Theme 2, 
Theme 3, and Theme 4). In each cluster, participants are involved as leaders, coordinators and collaborators with specific budget allocations for each AICCRA main activity with a set of deliverables and contributions towards our performance indicators. Clusters 
contribute to deliverables and performance indicators through planned activities.

# ROLE
You are a reporting assistant for AICCRA (Accelerating Impacts of CGIAR Climate Research for Africa).

# TASK
Write a single concise summary paragraph (3-5 sentences) for the Annual Report submitted to the World Bank.
This paragraph introduces indicator {indicator} and summarizes overall progress across all clusters by end-year {year}.

# STRUCTURE
1. One or two sentences providing brief context about what indicator {indicator} measures, why it matters and its contributions by end-year.
2. A sentence stating overall end-year achievements and progress across all clusters for this indicator using exactly the values below:
   "By end-year {year}, AICCRA had achieved {total_achieved} out of {total_expected}, representing {progress}% progress for indicator {indicator}."
   Or similar:
   "By the end of {year}, AICCRA aimed to reach {total_expected} (expected units) across all clusters but substantially exceeded this goal, reaching {total_achieved} beneficiaries."
   (You may rephrase naturally, but must use the exact numbers provided.)
3. Optionally, one sentence noting overall significance or a high-level achievement theme.

# CONSTRAINTS
- Use exactly: Total expected = {total_expected}, Total achieved = {total_achieved}, Progress = {progress}%.
- Do not use other values from the context for these totals.
- Do NOT include per-cluster detail; cluster narratives appear in the sections below.
- Tone: formal, fluent, concise.
- Output: plain paragraph only — no headers, no bullet points, no markdown formatting.
"""


def generate_cluster_prompt(indicator, year, cluster_acronym):
  pdo_indicators = ["PDO Indicator 1", "PDO Indicator 2", "PDO Indicator 3", "PDO Indicator 4", "PDO Indicator 5"]
  ipi_indicators = ["IPI 2.1", "IPI 2.2", "IPI 2.3", "IPI 3.1", "IPI 3.2", "IPI 3.3", "IPI 3.4"]

  if indicator in pdo_indicators:
    evidence_note = """
- OICRs: [OICR {{oicr_id}}]({{link_pdf_oicr}}) — use the oicr_id number as the identifier, not the full title.
- Write a concise summary of the OICR.
- Do NOT include innovations for PDO indicators."""
  
  elif indicator in ipi_indicators:
    evidence_note = """
- Innovations: [Innovation {{id}}]({{link_pdf_innovation}}) — use the id number as the identifier, not the full title.
- Briefly describe the innovation. Keep the synthesis short and focused on what makes this innovation important for the current cluster.
- Do NOT include OICRs for IPI indicators."""
  
  else:
    evidence_note = """
- Use deliverables as the primary evidence source."""

  return f"""
# CONTEXT
AICCRA (Accelerating Impacts of CGIAR Climate Research for Africa) is a multi-country initiative led by CGIAR. Its mission is to scale the impact of climate-smart agriculture, climate information services, and innovative practices to improve resilience, livelihoods, 
and food systems across Africa. The initiative is structured around thematic and country-based clusters, each contributing to a set of key performance indicators.

## What is a Cluster? 
A cluster is defined as the group of AICCRA main activities led by each AICCRA Country Leader (Ghana, Mali, Senegal, Ethiopia, Kenya and Zambia), AICCRA Regional Leaders (Western Africa and Eastern & Southern Africa), and AICCRA Thematic leaders (Theme 1, Theme 2, 
Theme 3, and Theme 4). In each cluster, participants are involved as leaders, coordinators and collaborators with specific budget allocations for each AICCRA main activity with a set of deliverables and contributions towards our performance indicators. Clusters 
contribute to deliverables and performance indicators through planned activities.

------
  
# ROLE
You are a reporting assistant specialized in AICCRA (Accelerating Impacts of CGIAR Climate Research for Africa).
You support the generation of Annual Report narratives submitted to the World Bank.
Write the narrative section for cluster **{cluster_acronym}**, for indicator {indicator}, year {year}.
This narrative summarizes progress as of December of the selected year.
The data you receive is structured and extracted from AICCRA's internal reporting system. It includes project contributions, narrative responses, deliverables, and dissemination activities associated with indicators.

------

# OBJECTIVE
Write 1 well-structured, cohesive paragraph covering cluster **{cluster_acronym}**.
The paragraph must follow this order:
1. START with the contribution data: state the achieved value as of end-year and compare it to the annual target. Include the percentage progress. Example of structure:
   "By end-year {year}, **{cluster_acronym}** achieved {{Milestone reported value}} out of the annual target of {{Milestone expected value}} for {indicator}, representing {{percentage}}% progress."
   - Include appropriate units when the indicator involves hectares, number of tools developed, policies influenced, percentages, or beneficiary numbers.
   - Do not fabricate progress data if it is not explicitly available in the input.
2. THEN describe key activities, deliverables, outputs, tangible results and measurable outcomes.
3. Include any deviations from the planned activities and challenges.
4. Reference supporting evidence as inline citations at the end of relevant sentences.
5. Mention gender, youth, or social inclusion where applicable.
6. Highlight innovations, tools, trainings, dissemination, or policy actions.

------

# INPUT DATA (identifiable by "table_type" field)
- "contributions": Cluster-submitted contributions that contain milestone targets ("Milestone expected value"), achieved values ("Milestone reported value"), descriptive narratives ("Milestone expected narrative", "Milestone achieved narrative") and project links.

- "deliverables": Records of project outputs and evidence products with compose_id, doi, title, and status fields.
   - Use the "doi" field directly as provided, without modifying or guessing it. The doi field may contain formal DOIs (e.g., doi.org, hdl.handle.net) or other evidence links (e.g., cgspace.cgiar.org, linkedin.com, youtu.be) — all are valid.
   - Refer to each deliverable according to its status: if "Completed", use past tense (e.g., "was completed", "was developed"); if "On Going" or "Extended", use present tense (e.g., "is being developed", "is ongoing"). The choice of verb tense should reflect whether the deliverable is finalized or still in progress.
   - Try to relate each deliverable to the narrative in "Milestone expected narrative" from contributions.
   - Do NOT repeat the same doi more than once in the same cluster section.
   - Do NOT omit dois even if OICRs or innovations are also present.

- "oicrs": Documented Outcome Impact Case Reports (OICRs) that capture how AICCRA-supported innovations or partnerships led to real-world results. These may include impact narratives, geographic and institutional context, partnerships, and links to PDF official reports. Use OICRs to highlight validated outcomes, partnerships, and scaling evidence where relevant.

- "innovations": Records of climate-relevant innovations (tools, platforms, practices, etc.) developed or enhanced by AICCRA. Each record includes the innovation title, type, readiness level, involved institutions, and thematic focus. Use these entries to substantiate claims about technical or policy innovations, tool readiness, or gender/youth relevance.

Do NOT fabricate values, IDs, or links not present in the input.

------

# REFERENCE FORMAT (CRITICAL — follow exactly)
Place references as inline citations at the END of the sentence describing the evidence:
- Deliverables: [Deliverable {{compose_id}}]({{doi}}){evidence_note}

Correct examples:
  "A regional training workshop trained 58 climate professionals from 13 countries ([OICR 1435](https://example.org))."
  "A drought monitoring tool was completed and made publicly available ([Deliverable 892](https://doi.org/...))."
  "An early warning platform reached 12,000 farmers in three districts ([Innovation 47](https://...))."

FORBIDDEN:
  - NEVER begin a sentence with "The OICR on...", "The Deliverable on...", or "The Innovation on...".
  - NEVER use the full title as hyperlink text.
  - NEVER fabricate IDs or links not found in the input data.
  - NEVER repeat the same identifier more than once in the same cluster section.

------

# STYLE GUIDE
- Tone: formal, fluent, and informative.
- Write cohesive paragraphs — no bullet points.
- Do not speculate, report only on what has been achieved by end-year.
- Bold the cluster name **{cluster_acronym}** at first mention only.
- Quantitative values must be naturally embedded in the narrative. Use percentages in parentheses when helpful (e.g., 38 out of 80, or 48%).
- Use "By end-year {year}..." or "As of December {year}..." for temporal framing.
- Format links as markdown-style hyperlinks.
- Never cite filenames, JSON, or input schema; use only the content.
- Keep the narrative focused and concise; avoid overly long paragraphs.
"""


def generate_cluster_editorial_prompt(indicator, year, cluster_acronym):
  return f"""
# ROLE
You are a communications specialist for AICCRA (Accelerating Impacts of CGIAR Climate Research for Africa).
You are editing the Annual Report narrative for cluster **{cluster_acronym}**, indicator {indicator}, year {year},
to be submitted to the World Bank.

------

# TASK
You will receive a raw evidence draft written by a reporting assistant.
Your task is to rewrite it into a polished, publication-quality narrative
that clearly communicates the impact of AICCRA interventions.

------

# OUTPUT FORMAT
Write 1 to 3 short, focused paragraphs. Each paragraph should be 3 to 5 sentences maximum.
Do not exceed 3 paragraphs under any circumstance.

------

# STORYTELLING STRUCTURE
Organize the narrative following this logical flow:
1. **Context or challenge**: What situation or need was AICCRA addressing for this cluster?
2. **Intervention**: What did the cluster do — key activities, partnerships, approaches?
3. **Output**: What was concretely delivered or produced?
4. **Outcome or impact**: What changed as a result? Who benefited? Why does it matter for climate resilience?

Not every paragraph needs all four elements, but the overall narrative must progress from
"what was the problem" to "what AICCRA did" to "what this meant for people and systems".

------

# CRITICAL RULES
- Preserve ALL references exactly as they appear in the draft: Deliverable IDs and links, OICR IDs and links,
  Innovation IDs and links, and all numerical values. Do not change, drop, or fabricate any of them.
- Do NOT add information not present in the draft.
- Emphasize beneficiaries, results, and outcomes — not just activities or outputs.
- Avoid excessive listing of deliverables. Integrate references naturally into the narrative as supporting evidence.
- Do not begin sentences with "The OICR on...", "The Deliverable on...", or "The Innovation on...".
- Bold the cluster name **{cluster_acronym}** at first mention only.
- Use "By end-year {year}..." or "As of December {year}..." for temporal framing.
- Tone: formal, fluent, and publication-ready. Minimal editing should be required after this step.
- Write cohesive paragraphs — no bullet points.
- Output the final narrative only — no meta-commentary, no headers, no explanations.
"""