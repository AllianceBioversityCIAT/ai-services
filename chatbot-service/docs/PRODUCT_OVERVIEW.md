# Product Overview – AICCRA Chatbot

---

## Problem Statement

AICCRA (Accelerating Impacts of CGIAR Climate Research for Africa) generates extensive program data across multiple country and thematic clusters, tracking performance indicators, research deliverables, innovations, and real-world outcomes. This data resides in complex database structures within MARLO-AICCRA, requiring technical expertise to navigate and extract insights.

Program managers, researchers, and reporting officers face significant operational friction when attempting to access specific data points or trends. Retrieving performance metrics, validating contributions, compiling evidence for donor reports, or identifying innovation readiness levels typically requires manual database queries, navigation through multiple reporting views, or reliance on technical staff support.

This creates bottlenecks in decision-making, delays in report preparation, and limits the accessibility of critical program intelligence to non-technical stakeholders. Strategic questions such as "What progress has been made on climate information services?" or "Which innovations are ready for scaling?" remain difficult to answer quickly or comprehensively.

The lack of intuitive data access also reduces the discoverability of insights that could inform resource allocation, identify performance gaps, or highlight breakthrough achievements across the multi-country initiative. As AICCRA scales, the volume and complexity of data continue to grow, further widening the gap between data availability and practical usability for program leadership and operational teams.

---

## Target Users

- **Program managers** – Monitor cluster performance, track milestones, and assess progress against targets
- **Reporting officers** – Extract data for donor reports, annual reviews, and compliance documentation
- **Researchers and technical staff** – Discover publications, research outputs, and innovation developments
- **Data validation teams** – Verify indicator contributions, narrative accuracy, and evidence completeness
- **Cluster coordinators** – Review deliverables, outcomes, and performance across thematic areas

---

## Beneficiaries

- **Senior management** – Access strategic insights for program oversight and high-level decision-making
- **Donors and funding partners** – Informed by accurate, evidence-based progress reporting and impact narratives
- **CGIAR institutional leadership** – Benefit from transparent performance tracking and outcome visibility
- **Country and regional stakeholders** – Supported by data-driven approaches to climate-smart agriculture scaling
- **African agricultural communities** – Ultimate beneficiaries of improved program efficiency and evidence-based resource deployment

---

## Access & Availability

**Access Method:**  
- REST API endpoint (`/api/chat`)
- Web-based interactive interface (HTML chatbot)

**Deployment Environment:**  
Serverless deployment via AWS Lambda with support for development, testing, and production environments.

**Integration Status:**  
Standalone service with programmatic access capabilities. Can be integrated into existing MARLO-AICCRA dashboards, reporting tools, or custom applications via REST API.

**Note:** Production URL provided through CGIAR infrastructure deployment configuration.

---

## Inputs

**Primary Input:**  
Natural language questions about AICCRA program data (e.g., "What innovations were developed for climate-smart agriculture in 2025?")

**Filter Parameters (Optional):**  
- **Reporting phase** – AWPB (planning), Progress (mid-year), Annual Report
- **Performance indicator** – IPI 1.1–3.4, PDO Indicator 1–5
- **Data section** – Deliverables, Contributions, Innovations, Outcome Impact Case Reports

**Session Management:**  
- Unique session identifier for conversation continuity
- User email address for personalized access control

**Data Source:**  
AICCRA program data stored in Microsoft SQL Server (Microsoft Fabric Lakehouse) containing deliverables, cluster contributions, innovation records, outcome case reports, milestone targets, and performance narratives.

**Input Method:**  
Manual text entry via web interface or JSON payloads via API for programmatic access.

---

## Outputs

**Natural Language Responses:**  
Conversational answers grounded in retrieved AICCRA data, providing contextual explanations, data summaries, and evidence-based insights.

**Rich Citations:**  
Hyperlinked references to source materials including:
- DOI links to research publications
- MARLO project pages with detailed contribution narratives
- PDF documents with innovation descriptions and outcome reports

**Aggregated Insights:**  
Cross-cluster, cross-phase, or cross-indicator summaries that synthesize performance patterns, deliverable status, or innovation readiness across multiple records.

**Contextual Recommendations:**  
Suggestions for query refinement, filter adjustment, or exploration of related data when initial results are insufficient or ambiguous.

**Output Delivery:**  
- Web interface: Real-time streaming responses displayed in chat UI
- API: JSON response objects with message content, applied filters, and status metadata
- Conversation history maintained throughout session for follow-up queries

---

## Value Proposition

**Democratizes Data Access:**  
Eliminates technical barriers, enabling non-technical staff to query complex program data using everyday language instead of SQL or database navigation.

**Accelerates Decision-Making:**  
Reduces time from question to insight from hours or days to seconds, enabling rapid responses to management inquiries, donor requests, or strategic planning needs.

**Improves Operational Efficiency:**  
Frees reporting officers and data analysts from repetitive data extraction tasks, allowing them to focus on analysis and interpretation rather than data retrieval.

**Enhances Report Quality:**  
Provides comprehensive, evidence-based responses with proper citations, improving the accuracy and credibility of donor reports, progress updates, and impact narratives.

**Increases Data Discoverability:**  
Surfaces insights that might otherwise remain hidden in database views, enabling proactive identification of performance gaps, high-impact innovations, and cross-cluster patterns.

**Scales with Program Growth:**  
Handles increasing data volumes without proportional increases in staff workload, supporting AICCRA's expansion across additional countries and thematic areas.

**Supports Evidence-Based Planning:**  
Enables strategic resource allocation, cluster performance comparison, and innovation readiness assessment based on real-time access to historical trends and performance patterns.

**Reduces Dependency on Technical Staff:**  
Empowers program teams to self-serve data needs, reducing bottlenecks created by limited availability of database administrators or data specialists.
