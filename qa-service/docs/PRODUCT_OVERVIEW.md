# Product Overview – PRMS QA Service (AI Review)

## Problem Statement

CGIAR's Performance & Results Measurement System (PRMS) captures thousands of research results annually across multiple result types (Innovation Development, Knowledge Products, Capacity Development, Policy Change, Innovation Use, and Other) and result levels (Output, Outcome, Impact). These results must be documented with titles, descriptions, and metadata that comply with institutional reporting standards while remaining accessible to non-specialist audiences including donors, policymakers, and partner organizations.

Reporting officers and research teams face significant challenges in producing quality metadata that meets CGIAR's strict formatting and content guidelines. Manual review and revision is time-intensive, inconsistent across teams, and prone to errors including technical jargon, unclear phrasing, non-compliance with word limits, and inadequate incorporation of supporting evidence. Additionally, result documentation must be enriched with evidence from multiple sources (publications, web pages, institutional repositories) requiring manual content extraction and synthesis.

Poor quality result metadata creates downstream risks: reduced transparency to donors, weakened institutional credibility, inconsistent reporting across programs, and delayed approval cycles as submissions are returned for revision. The manual quality assurance process does not scale effectively as reporting volume increases across CGIAR's expanding portfolio.

The PRMS QA Service addresses these operational inefficiencies by providing AI-powered automated quality review and metadata enhancement. It applies CGIAR-specific writing standards, result type and level-specific guidance, and evidence-based enrichment to systematically improve result documentation quality while reducing manual workload and ensuring consistency across the institution.

---

## Target Users

- **Reporting officers** who submit research results to PRMS
- **Research teams** preparing result documentation for institutional reporting
- **Project managers** overseeing reporting quality and compliance
- **Data validation teams** responsible for ensuring metadata meets CGIAR standards
- **Program coordinators** managing result submissions across multiple initiatives

---

## Beneficiaries

- **Senior management** – improved quality enables better decision-making and portfolio oversight
- **Donors and funding partners** – enhanced transparency and clarity in results reporting
- **Program and initiative leads** – consistent quality across all result types reduces review overhead
- **Institutional communications teams** – publication-ready content for external stakeholder engagement
- **External stakeholders** – accessible language improves understanding of CGIAR's research impact

---

## Access & Availability

**Production Access:**  
`https://dj3rjcpfvsiytr7ydjhmlc7ho40wglws.lambda-url.us-east-1.on.aws/api/prms-qa`

**User Access:** Through PRMS Reporting Tool interface – an AI review button is present on all result forms and becomes enabled when all required fields are completely filled out, allowing users to request automated quality enhancement

**Integration Mode:** Embedded service consumed by PRMS Reporting Tool frontend

**Deployment:** AWS Lambda (serverless), deployed in US-East-1 region

**Environment:** Production (with development and test environments available)

**API Documentation:** Available at `/docs` endpoint for developer reference

---

## Inputs

The module receives structured JSON metadata for each result submission:

- **Result identification** – result ID, result type (Innovation Development, Knowledge Product, etc.), result level (Output, Outcome, Impact)
- **Content fields** – original title, description, short name (for innovations)
- **Contextual metadata** – geographic scope, partner organizations, CGIAR center/program attribution
- **Impact area assessments** – user-provided scores and components across five dimensions (Gender Equality/Youth/Social Inclusion; Climate Adaptation/Mitigation; Nutrition/Health/Food Security; Environmental Health/Biodiversity; Poverty Reduction/Livelihoods/Jobs)
- **Supporting evidence** – URLs to publications, documents, and web resources (CGSpace repository links, PDFs, institutional pages)
- **User identifier** – for interaction tracking and analytics

Input is system-generated from the PRMS Reporting Tool interface as users complete result submission forms. Evidence URLs may be manually uploaded or pre-populated from existing PRMS records.

---

## Outputs

The module produces validated, standards-compliant result metadata:

**Primary outputs:**
- **Improved title** (maximum 30 words) – rewritten for clarity, non-specialist audiences, and compliance with result type/level guidelines
- **Improved description** (maximum 150 words) – enhanced with context, CGIAR contribution visibility, and evidence integration
- **Short name** (for Innovation Development results only) – concise, jargon-free identifier suitable for public communication
- **Impact area assessments** – refined scores and justifications across five CGIAR impact dimensions

**Metadata and analytics:**
- Processing time and performance metrics
- Interaction tracking ID for user analytics
- Evidence enrichment metadata (number of sources processed, successful extractions, validation warnings)
- Validation status and error handling information

**Storage and display:**  
Outputs are returned via REST API response to the PRMS Reporting Tool, where they are displayed side-by-side with original content for user review and acceptance. Users may accept, further edit, or regenerate suggestions before final submission to PRMS.

---

## Value Proposition

**Operational Efficiency:**  
Reduces manual quality review time from 15-30 minutes per result to under 2 minutes. Enables reporting officers to process higher volumes of results with consistent quality, freeing staff capacity for strategic work rather than repetitive editing tasks.

**Quality Assurance:**  
Systematically applies CGIAR writing standards across all result types and levels, ensuring compliance with formatting rules, word limits, audience appropriateness, and evidence integration requirements. Eliminates human inconsistency in applying complex, result-specific guidelines.

**Risk Mitigation:**  
Reduces submission rejection rates by catching non-compliance issues before formal review. Minimizes reputational risk from unclear or non-compliant external-facing documentation. Ensures donor-facing reports maintain institutional quality standards.

**Scalability:**  
Handles concurrent processing of multiple results without manual bottlenecks. Supports CGIAR's growing reporting portfolio as research programs expand. Maintains consistent quality regardless of reporting volume spikes during submission deadlines.

**Evidence Integration:**  
Automatically extracts and synthesizes content from publications, repositories, and web sources to enrich result context. Eliminates manual content review of supporting documents, enabling evidence-based metadata enhancement at scale.

**Strategic Importance:**  
Strengthens institutional credibility through consistent, high-quality results communication. Improves donor transparency and stakeholder trust. Positions CGIAR as a leader in AI-enhanced research management and reporting innovation. Provides data foundation for continuous improvement through interaction tracking and quality analytics.
