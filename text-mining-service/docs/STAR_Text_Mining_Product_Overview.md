# Product Overview – STAR Text Mining

---

## Problem Statement

CGIAR researchers and Alliance staff generate extensive documentation of capacity development activities, policy interventions, and innovation development initiatives across research programs. These documents—whether training reports, project deliverables, policy briefs, or technical papers—contain critical information about institutional impact, partner engagement, and development outcomes. However, this valuable data remains locked in unstructured formats, making systematic reporting and evidence-based decision-making challenging.

The current manual approach to extracting and structuring this information creates significant operational bottlenecks. Staff must read through lengthy documents, identify relevant activities aligned with specific result indicators, extract participant demographics and institutional details, cross-reference entity names with CGIAR's reference systems, and manually enter validated data into STAR. This process is time-intensive, prone to human error, and creates inconsistencies in how data is captured and standardized.

For organizations reporting to donors and stakeholders, incomplete or delayed results data creates visibility gaps in demonstrating institutional impact. Manual data entry also introduces variability in field mapping and entity resolution, leading to reporting inconsistencies that complicate aggregated analysis. As document volumes increase, the scalability of manual processing becomes a critical constraint.

The STAR Text Mining module addresses this challenge by automating the extraction and structuring of results data from unstructured documents, reducing manual workload while improving data quality, consistency, and timeliness. This enables the organization to demonstrate impact at scale while freeing staff to focus on higher-value analytical and strategic work.

---

## Target Users

The primary users who directly interact with this module are:

- **Reporting Officers** – Staff responsible for compiling results data for institutional reporting and donor accountability.
- **Research Program Managers** – Individuals overseeing projects who need to document outcomes related to capacity sharing, policy influence, and innovation development.
- **Alliance Project Staff** – Personnel who generate documentation and need structured outputs to be recorded in STAR.
- **Monitoring & Evaluation Teams** – Staff responsible for ensuring results data meets reporting standards and is linked to institutional indicators.
- **STAR Platform Users** – Any authenticated user within the STAR system with document processing needs.

---

## Beneficiaries

The following groups benefit indirectly from the module's outputs:

- **Senior Management & Leadership** – Gain visibility into aggregated results data for strategic decision-making and institutional reporting.
- **Donors & Funding Partners** – Receive evidence-based reporting on capacity development reach, policy contributions, and innovation pipelines.
- **Program & Initiative Leads** – Benefit from consolidated insights across projects and geographies without manual data compilation.
- **CGIAR Research Centers** – Leverage improved data consistency for cross-center collaboration and impact assessment.
- **External Partners & Collaborators** – Organizations mentioned in results benefit from proper entity recognition and linkage to CGIAR reference systems.

---

## Access & Availability

Access provided through **STAR Platform**.

The module operates as a backend AI service embedded within the STAR platform. Users do not access the module directly; instead, they interact with STAR's interface, which invokes the text mining service via API calls.

- **Deployment:** AWS Lambda (serverless microservice)
- **Endpoint:** `/star/text-mining` (REST API)
- **Environments:** Configurable via `environmentUrl` parameter (supports production, test, and development instances)
- **Authentication:** All requests require valid STAR authentication tokens

The module is not standalone—it functions exclusively as part of the STAR ecosystem and relies on STAR's authentication and user interface layers for access management.

---

## Inputs

The module accepts documents in multiple formats and processes them with contextual parameters:

**Document Formats:**
- PDF (`.pdf`)
- Microsoft Word (`.docx`, `.doc`)
- Excel spreadsheets (`.xlsx`, `.xls`) – processed row-by-row for structured data
- PowerPoint presentations (`.pptx`, `.ppt`)
- Plain text files (`.txt`)

**Document Sources:**
- **Direct Upload** – Users upload files through the STAR interface
- **S3 Reference** – Users specify existing document keys in AWS S3 storage

**Additional Inputs:**
- **Authentication Token** – Validates user permissions via STAR authorization service
- **Environment URL** – Specifies target environment (production, test, development)
- **User ID (Optional)** – Enables interaction tracking for feedback collection and service improvement

Documents are analyzed against predefined indicator prompts that guide AI extraction toward three result types: Capacity Sharing for Development, Policy Change, and Innovation Development.

---

## Outputs

The module produces structured, validated data in JSON format, ready for integration into STAR's knowledge management system.

**Primary Output Structure:**
- **Result Records** – Each representing a distinct indicator-aligned outcome
- **Indicator Type** – Categorized as Capacity Development, Policy Change, or Innovation Development
- **Core Metadata** – Title, description, keywords, contact person details
- **Geographical Scope** – Hierarchical geographic coverage (global, regional, national, sub-national) with standardized UN49 region codes and ISO Alpha-2 country codes
- **Indicator-Specific Fields** – Custom attributes based on result type (e.g., participant counts, training modalities, policy stages, innovation readiness levels)

**Enhanced Data Quality Features:**
- **Entity Resolution** – Extracted names (staff, institutions, organizations) are mapped to canonical identifiers using CGIAR's reference systems via integration with the Field Mapping Service
- **Validation** – All outputs conform to Pydantic schemas ensuring type safety and business rule compliance
- **Similarity Scores** – Entity mappings include confidence scores for validation review

**Operational Metadata:**
- **Processing Time** – Enables performance monitoring
- **Interaction ID** – Links outputs to user sessions for feedback workflows
- **Error Annotations** – Partial success scenarios include descriptive error messages

**Output Destinations:**
- Returned as structured JSON to STAR platform for display or storage
- Interaction tracking service records outputs for continuous improvement
- Slack notifications sent to operational teams on completion status

---

## Value Proposition

The STAR Text Mining module delivers measurable value across multiple dimensions:

**Efficiency Gains:**
- Transforms hours of manual data extraction into seconds of automated processing
- Eliminates repetitive reading and manual transcription tasks
- Scales processing capacity to handle large volumes of documents without proportional increases in staffing

**Risk Reduction:**
- Minimizes human error in data capture and entity naming
- Enforces validation rules at extraction time, preventing downstream data quality issues
- Standardizes geographical and entity references against institutional reference systems (CLARISA)

**Quality Improvement:**
- Ensures consistency in how results are interpreted and categorized
- Applies uniform extraction logic across all documents, reducing subjective variation
- Leverages AI-powered semantic understanding to identify results data even when not explicitly labeled

**Strategic Scalability:**
- Enables the organization to process increasing document volumes without linear cost growth
- Supports real-time or near-real-time reporting as documents are produced
- Frees staff capacity for higher-value activities such as analysis, strategic planning, and stakeholder engagement

**Institutional Impact:**
- Provides comprehensive, evidence-based reporting to donors and stakeholders
- Improves visibility into capacity development reach, policy influence, and innovation pipelines
- Enables data-driven decision-making with timely, accurate results data
- Positions CGIAR as a leader in leveraging AI for institutional effectiveness and research impact transparency

By automating the transformation of unstructured documents into structured, validated results data, the module directly supports CGIAR's mandate to demonstrate measurable development impact while reducing operational burden on staff.

---

**Document Control:**  
**Version:** 1.0  
**Date:** February 26, 2026  
**Prepared By:** Senior Product Manager  
**Module:** STAR Text Mining
