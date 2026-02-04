# AICCRA Chatbot Service – Technical Documentation

---

## Service Overview

The AICCRA Chatbot Service is an AI-powered conversational interface designed to provide natural language access to AICCRA (Accelerating Impacts of CGIAR Climate Research for Africa) program data. The service enables stakeholders to query and explore project information including deliverables, contributions, innovations, outcome reports, and performance indicators through an intuitive chat interface.

**Primary Use Cases within MARLO-AICCRA:**
- **Progress monitoring** – Track cluster performance against annual targets and milestones
- **Data exploration** – Query deliverables, innovations, and outcomes across reporting phases
- **Impact assessment** – Retrieve outcome case reports and real-world impact evidence
- **Performance insights** – Analyze indicator progress and contribution narratives
- **Knowledge retrieval** – Access research outputs, publications, and technical documentation with citations

---

## Data Sources

**Primary Data Repository:**  
Microsoft SQL Server database (Microsoft Fabric Lakehouse) serves as the single source of truth for all AICCRA program data.

**Data Types Processed:**
- **Structured program data** – Performance indicators, milestones, targets, and reported values
- **Narrative text** – Contribution narratives, questions, and progress descriptions
- **Deliverable metadata** – Publications, reports, tools, and research outputs with DOI links
- **Innovation records** – Technologies, platforms, practices, and readiness assessments
- **Outcome case reports (OICRs)** – Impact stories and real-world application evidence
- **Institutional metadata** – Clusters, indicators, phases, categories, and classifications

**Data Organization:**  
Data is organized by:
- **Reporting phases** – AWPB (Annual Work Plan & Budget), Progress (mid-year), AR (Annual Report)
- **Performance indicators** – IPI (Intermediate Performance Indicators) and PDO (Project Development Objective indicators)
- **Clusters** – Country-based, regional, and thematic organizational units
- **Years** – Calendar year-based tracking (2021-2025+)

---

## Data Collection & Ingestion

**Data Extraction:**  
The service extracts data from multiple database views that consolidate AICCRA program information from the MARLO-AICCRA system. Each view represents a specific data domain (contributions, deliverables, innovations, outcomes, questions).

**Data Access Method:**  
- SQL Server connection via authenticated client credentials
- Query execution against predefined database views
- Pandas-based data processing for transformation and structuring

**Preprocessing Steps:**
1. **Data retrieval** – Query database views and load results into dataframes
2. **Format transformation** – Convert structured records into JSONL format for knowledge base ingestion
3. **Metadata enrichment** – Add classification fields (phase, year, indicator, table type) to enable filtering
4. **File generation** – Produce JSONL files where each line represents a single data record
5. **File segmentation** – Divide large JSONL files into smaller chunks to optimize vector processing

**Optional Data Refresh:**  
Users can trigger a data reload operation that re-ingests fresh data from the database, processes it, and synchronizes the knowledge base. This operation takes several minutes due to the volume of records processed.

---

## AI Processing Pipeline

**High-Level Processing Flow:**

1. **User query submission** – User submits a natural language question with optional filters (phase, indicator, section)

2. **Filter application** – User-specified filters are translated into metadata query constraints that limit the knowledge base search scope

3. **Session management** – Each conversation is tracked via a unique session ID to maintain context across multiple messages

4. **Vector-based retrieval** – The user question is processed to retrieve semantically relevant documents from the knowledge base using similarity search

5. **Context assembly** – Retrieved documents are provided as context to the language model along with the user's question and filter information

6. **AI response generation** – The language model generates a contextual answer grounded in the retrieved evidence

7. **Streaming response delivery** – The answer is streamed back to the user in real-time, token-by-token

**Key Processing Mechanisms:**

- **Semantic search** – User questions are matched against pre-indexed knowledge base content using vector similarity
- **Metadata filtering** – Dynamic filters (phase, indicator, section) narrow the retrieval scope before semantic matching
- **Memory integration** – Conversation history is maintained across sessions to enable follow-up questions and context awareness
- **Response grounding** – The model is instructed to answer only using retrieved content and to cite sources with hyperlinks

---

## Models & AI Technologies

**Language Model:**  
Amazon Bedrock Agents with **Claude 3.7 Sonnet** foundation model.

**Role:** Conversational AI that interprets user queries, processes context, and generates natural language responses. The model is configured with custom instructions tailored to AICCRA domain knowledge, ensuring accurate interpretation of indicators, clusters, and reporting phases.

**Embedding Model:**  
Amazon Bedrock Knowledge Base uses its default embedding model for vectorization.

**Role:** Converts text documents into dense vector representations that enable semantic similarity search. Text chunks from AICCRA data are embedded and indexed in a vector database.

**Agent Architecture:**  
AWS Bedrock Agents orchestrates the complete interaction flow including session management, knowledge base retrieval, and response generation. The agent maintains conversation memory and applies retrieval filters dynamically based on user inputs.

---

## Supporting Technologies & Architecture

**Cloud Infrastructure:**
- **AWS Bedrock** – Managed AI service for agents, knowledge bases, and foundation models
- **AWS S3** – Object storage for JSONL data files that feed the knowledge base
- **Amazon OpenSearch** – Vector database backend for knowledge base indexing and similarity search

**Application Layer:**
- **FastAPI** – REST API framework providing HTTP endpoints for programmatic access
- **HTML/JavaScript** – Web-based user interface for interactive chatbot sessions
- **Uvicorn** – ASGI server for running the FastAPI application
- **Mangum** – AWS Lambda adapter for serverless deployment

**Data Processing:**
- **Pandas** – Data transformation and JSONL generation from database queries
- **SQLAlchemy** – Database connectivity and query execution
- **Boto3** – AWS SDK for S3 uploads and Bedrock service integration

**Conceptual Interaction Flow:**

1. User interacts via REST API or HTML web interface
2. User query + filters → FastAPI endpoint → Bedrock Agent
3. Bedrock Agent applies metadata filters → queries Knowledge Base
4. Knowledge Base retrieves relevant chunks from OpenSearch vector index
5. Claude 3.7 Sonnet generates response using retrieved context
6. Response streamed back through API → displayed to user

---

## Front-End & User Interaction

**Access Methods:**

**1. REST API**  
Programmatic access via HTTP POST requests to `/api/chat` endpoint. Suitable for integration with external applications, dashboards, or custom interfaces.

**2. HTML Web Interface**  
Interactive browser-based chat interface with conversation history, dynamic filter controls, and modern UI design. Suitable for direct human interaction.

**User Inputs:**

- **Message (required)** – Natural language question or query about AICCRA data
- **Session ID (required)** – Unique identifier to maintain conversation continuity across multiple messages
- **Memory ID (required)** – User email address for personalized access control
- **Phase (optional)** – Filter by reporting phase (AWPB, Progress, AR) and year
- **Indicator (optional)** – Filter by specific performance indicator (e.g., IPI 1.1, PDO Indicator 3)
- **Section (optional)** – Filter by data type (Deliverables, Innovations, OICRs, Contributions)
- **Insert Data (optional)** – Boolean flag to trigger fresh data reload from database

**User Interaction Flow:**

1. User formulates a question (e.g., "What innovations were developed for climate-smart agriculture in 2025?")
2. User optionally applies filters to narrow the scope
3. System processes query and retrieves relevant information
4. AI generates a response with citations and hyperlinks to source documents
5. User can ask follow-up questions that build on previous context
6. Conversation history is preserved throughout the session

**Example Questions:**
- "What progress has been made on IPI 1.1 in 2025?"
- "Show me deliverables from the Kenya cluster related to climate information services"
- "What is the readiness level of innovations developed by Theme 2?"
- "How has AICCRA contributed to farmer livelihoods in Western Africa?"

---

## Outputs & Value

**Service Outputs:**

**1. Natural Language Responses**  
Conversational answers to user questions, generated in real-time and grounded in retrieved AICCRA data. Responses include explanations, data summaries, and contextual information.

**2. Citations & Links**  
Hyperlinks to source documents including:
- DOI links to publications
- MARLO project pages with detailed contribution narratives
- PDF links to innovation descriptions and outcome reports

**3. Data Summaries**  
Aggregated insights across multiple records, clusters, or indicators. For example, summarizing deliverables across all clusters or progress across multiple years.

**4. Contextual Recommendations**  
Suggestions for refining queries or exploring related information when results are insufficient or ambiguous.

**Value to AICCRA Stakeholders:**

**For Program Managers:**
- Rapid access to performance data without navigating complex database views
- On-demand progress tracking against targets and milestones
- Quick identification of high-performing clusters and lagging indicators

**For Researchers & Technical Staff:**
- Efficient discovery of relevant publications and research outputs
- Easy exploration of innovations and their readiness levels
- Quick access to outcome case reports demonstrating real-world impact

**For Reporting & Compliance:**
- Simplified data extraction for report generation
- Quick validation of indicator contributions and narratives
- Easy compilation of evidence for specific themes or regions

**For Decision-Making:**
- Informed strategic planning based on historical performance patterns
- Identification of gaps in deliverables or contributions
- Evidence-based resource allocation across clusters and themes

**Overall Impact:**  
The service democratizes access to AICCRA program data by removing technical barriers and enabling natural language interaction with complex structured information. It accelerates decision-making, reduces time spent on data retrieval, and improves the discoverability of insights that would otherwise require manual database queries or report review.

---

## Summary

The AICCRA Chatbot Service transforms how stakeholders interact with program data by providing an intelligent, conversational interface powered by advanced AI technologies. By combining semantic search, session memory, and domain-tailored language models, the service delivers accurate, contextual, and actionable insights directly from AICCRA's reporting infrastructure.

The system's architecture leverages cloud-native AWS services for scalability, reliability, and performance while maintaining a clean separation between data sources, AI processing, and user-facing interfaces. This design ensures the service can scale with AICCRA's growing data volumes and evolving user needs.
