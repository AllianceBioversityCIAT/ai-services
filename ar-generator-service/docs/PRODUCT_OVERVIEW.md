# Product Overview – AICCRA Report Generator

## 1. Problem Statement

AICCRA (Accelerating Impacts of CGIAR Climate Research for Africa) is required to submit comprehensive annual and mid-year progress reports to the World Bank and other institutional donors. These reports document performance across multiple indicators, covering achievements from 2020 to 2030, and must synthesize complex project data including performance metrics, deliverables, cluster contributions, innovations, and impact case studies.

Historically, report generation was a manual, labor-intensive process requiring staff to extract data from multiple databases, review hundreds of documents, synthesize narratives, and ensure compliance with World Bank reporting standards. A single comprehensive annual report could take days or weeks to prepare, often requiring multiple reviewers to ensure accuracy and consistency. This created several critical challenges: significant staff time diverted from strategic activities, potential for human error in data synthesis, inconsistent narrative quality across reporting cycles, and delayed submission timelines.

The manual process also created a scalability bottleneck. With multiple indicators (IPI 1.1–3.4 and PDO 1–5) and annual reporting requirements, the workload grew unsustainably, particularly during peak reporting periods. Additionally, narrative quality and tone varied depending on who authored each section, complicating stakeholder reviews.

This module solves these challenges by automating the end-to-end report generation process, transforming weeks of manual work into minutes of AI-assisted synthesis while maintaining consistency, accuracy, and compliance with donor requirements.

## 2. Target Users

**Primary Users:**
- **Reporting Officers** – Staff responsible for compiling and submitting annual and mid-year progress reports to donors
- **Program Managers** – AICCRA program leads who oversee indicator performance and need comprehensive progress documentation
- **M&E (Monitoring & Evaluation) Teams** – Teams tracking performance metrics and requiring data-driven narrative reports
- **MARLO Platform Users** – Staff working within CGIAR's Managing Agricultural Research for Learning and Outcomes (MARLO) system

**Secondary Users:**
- **Technical Coordinators** – Staff who validate report content against source data before final submission
- **Data Entry Teams** – Personnel who maintain structured data in the AICCRA Lakehouse database

The module is designed for both technical and non-technical users, offering both a web interface for simplified access and REST API endpoints for integration into existing workflows.

## 3. Beneficiaries

**Direct Beneficiaries:**
- **World Bank** – Primary institutional donor receiving standardized, timely progress reports that meet reporting requirements
- **CGIAR Senior Leadership** – Executive stakeholders who rely on comprehensive reporting for strategic decision-making and donor relations
- **AICCRA Program Directors** – Leadership overseeing the program who need evidence-based documentation of achievements

**Indirect Beneficiaries:**
- **Institutional Donors and Partners** – Organizations funding or collaborating with AICCRA who benefit from transparent reporting
- **Country Program Leads** – Regional stakeholders who use reports to demonstrate impact and justify continued investment
- **Policy Makers** – Government and institutional decision-makers who use AICCRA reports to inform climate adaptation policies
- **End Stakeholders (Farmers and Communities)** – Beneficiaries of AICCRA interventions whose outcomes are documented and communicated through these reports

## 4. Access & Availability

**Production Environment:**
- **Web Interface**: [https://ia.prms.cgiar.org/web/](https://ia.prms.cgiar.org/web/)
- **API Endpoint**: `https://ia.prms.cgiar.org/api/`
- **Interactive API Documentation**: [https://ia.prms.cgiar.org/docs](https://ia.prms.cgiar.org/docs) (Swagger UI for testing endpoints)
- **MARLO Platform Integration**: Accessible through MARLO's AICCRA AI Module at [https://aiccratest.ciat.cgiar.org/ai/AICCRA/ai.do?edit=true&phaseID=428](https://aiccratest.ciat.cgiar.org/ai/AICCRA/ai.do?edit=true&phaseID=428)

**Development Environment:**
- Local development: `http://localhost:8000/web/`

**Deployment Model:**
- Standalone microservice integrated with the MARLO platform ecosystem
- Deployable to AWS Lambda (serverless) or traditional server environments
- Production deployment hosted on CGIAR infrastructure

**Access Control:**
- Currently relies on AWS IAM authentication for API-level security
- Web interface accessible to authorized CGIAR staff
- No user authentication layer at the application level (handled at infrastructure level)

**Availability:**
- Operates as an on-demand service (request-response model)
- Background data refresh jobs scheduled weekly (Sundays at 2:00 AM)
- High availability during reporting periods (mid-year and year-end)

## 5. Inputs

**User-Provided Inputs:**
- **Indicator Selection** – AICCRA performance indicator identifier (e.g., IPI 1.1, PDO Indicator 3)
- **Reporting Year** – Target year for report generation (2021–2025 currently supported)
- **Data Refresh Preference** – Optional flag to refresh vector database with latest source data

**System-Generated Inputs (from AICCRA Lakehouse):**
- **Performance Metrics** – Quantitative targets, achievements, and progress percentages
- **Deliverables Data** – Publications, datasets, tools, and outputs with DOI links and metadata
- **Cluster Contributions** – Activity descriptions and outcomes from regional implementation clusters
- **OICR Records** – Outcome Impact Case Reports documenting impact pathways and evidence
- **Innovation and Technology Data** – New methodologies, tools, and technologies developed
- **Indicator Metadata** – Definitions, measurement units, baselines, and disaggregation categories

**Data Sources:**
- SQL Server database (AICCRA Lakehouse) containing structured project data
- Pre-defined database views dynamically created to join fact and dimension tables
- Historical report data and context stored in Amazon OpenSearch vector database

**Input Format:**
- Web form selections (user-friendly dropdown menus for indicators and years)
- JSON payloads for API requests (programmatic access)

## 6. Outputs

**Report Types Generated:**

1. **Mid-Year Progress Reports** – Narrative summaries of progress achieved from January to mid-year for specific indicators
2. **Comprehensive Annual Reports** – Full-year assessments including achievements, challenges, innovations, and strategic recommendations
3. **Challenges and Lessons Learned Reports** – Cross-cluster analyses synthesizing implementation challenges and adaptive strategies
4. **Annual Indicator Summary Tables** – Quantitative overviews of all indicators grouped by type (IPI vs. PDO)

**Output Format:**
- **Primary Format**: Markdown-formatted narrative text optimized for readability and editing
- **Secondary Formats**: Downloadable as DOCX (Word) or XLSX (Excel) via web interface

**Content Structure:**
- Executive summaries with quantitative achievement vs. target comparisons
- Detailed narrative sections covering deliverables, cluster activities, and innovations
- Evidence-based content with DOI links to publications and datasets
- Gender and social inclusion analysis (where applicable)
- Risk assessments and mitigation strategies
- Strategic recommendations and lessons learned

**Output Delivery:**
- JSON responses via REST API (programmatic integration)
- Rendered HTML display in web interface (browser-based access)
- Stored temporarily in application memory (not persisted in database)

**Output Destination:**
- Displayed directly to users for immediate review and editing
- Exported to user's local system for further refinement and submission

## 7. Value Proposition

**Efficiency Gains:**
The module reduces report generation time from days or weeks to minutes, automating data retrieval, synthesis, and narrative generation. Staff previously required to manually compile reports can redirect effort toward strategic analysis, stakeholder engagement, and program improvement. Peak reporting periods no longer create operational bottlenecks.

**Risk Reduction:**
Automated data extraction eliminates manual transcription errors. Consistent AI-driven synthesis reduces the risk of omitting critical information or misinterpreting data. Standardized narrative structure ensures compliance with World Bank reporting requirements, reducing the risk of report rejection or revision requests.

**Quality Improvement:**
AI-powered narrative generation leverages advanced language models to produce coherent, professional reports with consistent tone and structure. The system synthesizes information from hundreds of source documents and database records, ensuring comprehensive coverage impossible to achieve manually. Evidence-based narratives include direct links to DOI-registered deliverables, enhancing credibility and traceability.

**Scalability:**
The module handles multiple indicators (currently 12 IPI and 5 PDO indicators) and multiple years without additional staff resources. As AICCRA expands or reporting requirements increase, the system scales seamlessly. Background data refresh processes ensure the system remains current without manual intervention.

**Strategic Importance:**
The module strengthens CGIAR's institutional reputation by ensuring timely, high-quality reporting to the World Bank and other donors. Consistent, professional reports support continued funding and demonstrate accountability. The system also enables rapid report generation for ad-hoc requests, improving responsiveness to stakeholder needs. By embedding AI capabilities within existing workflows, the module positions CGIAR as a technology-forward research organization leveraging innovation in operational processes.

The solution transforms reporting from a reactive compliance burden into a strategic asset that communicates impact, justifies investment, and supports data-driven decision-making across the AICCRA program and broader CGIAR ecosystem.
