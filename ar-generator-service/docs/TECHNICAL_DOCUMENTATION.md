# AICCRA Reports Generator Service – Technical Documentation

## Service Overview

### Purpose
The AICCRA Reports Generator Service is an AI-powered application that automates the generation of comprehensive progress reports for the AICCRA (Accelerating Impacts of CGIAR Climate Research for Africa) initiative. The service transforms structured project data from MARLO-AICCRA into narrative reports using advanced language models and vector search capabilities.

### Main Use Cases
- **Mid-Year Progress Reports**: Generate interim reports tracking progress achieved from January to mid-year for specific performance indicators.
- **Annual Reports**: Produce comprehensive year-end reports covering full-year achievements, impact assessments, and detailed cluster contributions.
- **Disaggregated Target Analysis**: Generate detailed breakdowns of indicator performance by demographics, geography, and technology type.
- **Challenges & Lessons Learned**: Compile cross-cluster analyses of implementation challenges and strategic recommendations.
- **Indicator Tables**: Create structured summaries of quantitative achievements across multiple indicators and time periods.

---

## Data Sources

### Primary Data Source
The service retrieves data from a **SQL Server database** (AICCRA Lakehouse) that stores structured information collected through the MARLO-AICCRA reporting platform. This database contains real-time project data submitted by cluster coordinators and project teams across Africa.

### Data Categories
1. **Project Contributions**: Quantitative progress data, milestone tracking, narrative descriptions, and cluster-specific achievements.
2. **Deliverables**: Research outputs including publications, datasets, tools, and policy briefs with DOI links and metadata.
3. **Outcome Impact Case Reports (OICRs)**: Documented case studies demonstrating real-world impact of AICCRA interventions.
4. **Innovations**: Climate-relevant technologies, platforms, and practices developed or validated by AICCRA.
5. **Questionnaire Responses**: Detailed answers to indicator-specific disaggregation questions.

### Data Structure
The system processes data filtered by:
- **Indicator**: Performance indicators (IPI 1.1-3.4, PDO Indicator 1-5)
- **Year**: Target reporting year (2021-2025)
- **Cluster**: Regional or thematic cluster (Ghana, Mali, Kenya, Western Africa, Theme 1, etc.)

---

## Data Collection & Ingestion

### Data Extraction Process
1. **Database Views Creation**: The service dynamically creates or updates SQL views that join dimensional and fact tables, enriching data with cluster names, indicator descriptions, institutional affiliations, and geographic information.

2. **Data Retrieval**: Executes parameterized SQL queries against five primary views:
   - `vw_ai_project_contribution`: Progress metrics and narrative contributions
   - `vw_ai_deliverables`: Research outputs with DOIs and dissemination formats
   - `vw_ai_oicrs`: Impact case reports with evidence links
   - `vw_ai_innovations`: Technology readiness and innovation metadata
   - `vw_ai_questions`: Disaggregated target responses

3. **Authentication**: Uses Azure Active Directory Service Principal authentication for secure database access.

### Data Preprocessing
1. **Column Standardization**: Renames columns for consistency and drops unnecessary fields (IDs, internal codes).
2. **Data Cleaning**: Removes empty columns and null values to reduce noise in AI processing.
3. **Aggregation**: Groups deliverables, OICRs, and innovations by unique identifiers to consolidate related data.
4. **Type Labeling**: Adds a `table_type` field to distinguish data sources during AI generation.
5. **Serialization**: Converts cleaned dataframes to JSON format for downstream vectorization.

---

## AI Processing Pipeline

### Step 1: Document Chunking
Each database record is converted into a JSON-formatted text chunk representing a single semantic unit (one contribution, one deliverable, etc.). This preserves all relevant metadata while creating meaningful retrieval units.

### Step 2: Text Vectorization
- **Embedding Model**: Amazon Titan Text Embeddings v2
- **Process**: Each text chunk is converted into a 1024-dimensional vector that captures semantic meaning.
- **Purpose**: Enables similarity-based retrieval of contextually relevant information.

### Step 3: Vector Storage & Indexing
- **Index Creation**: Creates an OpenSearch index with k-NN (k-nearest neighbors) configuration.
- **Index Structure**: 
  - Vector field using HNSW (Hierarchical Navigable Small World) algorithm with cosine similarity
  - Metadata fields for filtering (indicator, year, source table)
- **Storage**: Each document is indexed with its embedding and original chunk data.

### Step 4: Contextual Retrieval
- **Query Vectorization**: User query (indicator + year + report prompt) is converted to a vector.
- **Hybrid Search**: Combines vector similarity search with metadata filtering to retrieve top-k most relevant documents.
- **Filtering Strategy**: Applies boolean filters to ensure retrieved documents match the exact indicator, year, and relevant data sources.

### Step 5: Report Generation
- **Prompt Engineering**: Constructs specialized prompts based on report type. Each prompt contains:
  - **Context Section**: Explains AICCRA's structure, clusters, and indicator definitions
  - **Role Definition**: Establishes the AI as a specialized AICCRA reporting assistant
  - **Objective**: Specifies the exact narrative requirements and evidence standards
  - **Input Schema**: Describes the structure of retrieved data (table types, fields, filtering rules)
  - **Output Requirements**: Defines format, word limits, number of required evidence links, and citation style
  - **Style Guidelines**: Sets tone, vocabulary, and formatting rules aligned with World Bank standards
  - Prompts are dynamically customized with indicator-specific instructions, year parameters, and quantitative summaries
- **Context Assembly**: Retrieved documents are formatted as structured context for the language model.
- **LLM Invocation**: Sends prompt + context to the language model with parameters optimized for factual reporting.
- **Response Streaming**: Processes model responses in real-time to provide progressive feedback.

---

## Models & AI Technologies

### Language Model
- **Model**: Claude 3.7 Sonnet (Anthropic) via AWS Bedrock
- **Purpose**: Generates coherent, evidence-based narrative reports from structured data.
- **Parameters**: 
  - Temperature: 0.1 (for factual consistency)
  - Max tokens: 8000 (to accommodate comprehensive reports)
  - Top-p: 0.999 (for controlled randomness)
- **Role**: Synthesizes retrieved context into structured narratives following AICCRA reporting standards.

### Embedding Model
- **Model**: Amazon Titan Text Embeddings v2
- **Purpose**: Converts text into high-dimensional vectors for semantic similarity search.
- **Dimension**: 1024-dimensional embeddings
- **Role**: Enables intelligent retrieval of contextually relevant information from thousands of database records.

---

## Supporting Technologies & Architecture

### Core Infrastructure
- **API Framework**: FastAPI for high-performance REST endpoints with automatic OpenAPI documentation.
- **Vector Database**: Amazon OpenSearch Service with k-NN capabilities for semantic search at scale.
- **Relational Database**: SQL Server with Azure Active Directory authentication for structured data storage.
- **Cloud Platform**: AWS services for AI models, vector storage, and object storage.

### Key Technologies
- **AWS Bedrock**: Managed service for accessing foundation models (Claude 3.7 Sonnet, Titan Embeddings).
- **OpenSearch**: Distributed search engine with vector search support using HNSW indexing.
- **Boto3**: AWS SDK for Python enabling programmatic access to Bedrock and S3.
- **PyODBC**: Database connectivity driver for SQL Server integration.
- **Pandas**: Data manipulation and transformation library.
- **Requests AWS4Auth**: AWS Signature Version 4 authentication for OpenSearch HTTP requests.

### Conceptual Architecture
```
┌─────────────────┐
│   MARLO-AICCRA  │ (User Input)
│   Web Interface │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI Server │ (API Layer)
└────────┬────────┘
         │
         ├─────────────────────────┐
         ▼                         ▼
┌──────────────────┐      ┌─────────────────┐
│  SQL Server      │      │  OpenSearch     │
│  (Raw Data)      │      │  (Vector Index) │
└────────┬─────────┘      └────────┬────────┘
         │                         │
         │  Data Extraction        │  Retrieval
         ▼                         │
┌──────────────────┐              │
│  Data Processing │              │
│  & Vectorization │──────────────┘
└──────────────────┘
         │
         ▼
┌──────────────────┐
│   AWS Bedrock    │
│ (Claude 3.7 +    │
│  Titan Embed)    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Generated Report│ (Output)
└──────────────────┘
```

---

## Front-End & User Interaction

### Access Methods

**1. Web Interface** (`/web/`)
- Browser-based UI hosted within the service
- Interactive forms for selecting report type, indicator, and year
- Real-time progress indicators during report generation
- Display of formatted markdown reports with copy-to-clipboard functionality
- Accessible to MARLO-AICCRA users without API knowledge

**2. REST API** (`/api/generate`, `/api/generate-annual`, etc.)
- Programmatic access for system integration
- JSON request/response format
- Can be called from MARLO-AICCRA backend for automated report generation
- Supports both synchronous and streaming response modes

### User Inputs
Users specify three primary parameters:
1. **Indicator**: The performance metric to report on (e.g., "IPI 1.1", "PDO Indicator 2")
2. **Year**: The reporting year (2021-2025)
3. **Data Refresh Flag** (optional): Whether to reload fresh data from the database into the vector index

### Interaction Flow
1. User selects report type (Mid-Year or Annual) via tabs
2. User enters indicator, year, and data refresh preference
3. System validates inputs and initiates processing
4. Progress indicators show current stage (data retrieval, vectorization, AI generation)
5. Generated report appears in markdown format with active hyperlinks
6. User can copy report to clipboard for integration into MARLO-AICCRA

---

## Outputs & Value

### Generated Reports
The service produces structured narrative reports in markdown format containing:
- **Quantitative Summaries**: Total expected vs. achieved values with progress percentages
- **Cluster-Specific Narratives**: Individual achievement descriptions for each contributing cluster
- **Evidence Links**: Active hyperlinks to deliverables (DOIs), OICR PDFs, and innovation documentation
- **Cross-Cutting Themes**: Gender, youth engagement, and social inclusion highlights
- **Geographic Context**: Country and regional scope of activities

### Output Formats
- **Mid-Year Reports**: Concise single-paragraph summaries (≤250 words) with minimum 5 evidence links
- **Annual Reports**: Multi-section comprehensive reports including executive summary, cluster narratives, and disaggregated targets
- **Indicator Tables**: Structured HTML tables with quantitative achievement data
- **Challenges Reports**: Cross-cluster analysis of implementation difficulties and lessons learned

### Value Proposition
1. **Time Efficiency**: Reduces report writing from hours to minutes, enabling coordinators to focus on strategic activities.
2. **Consistency**: Ensures uniform report structure and terminology across all clusters and indicators.
3. **Evidence-Based**: Automatically incorporates DOI links and validated data, strengthening report credibility.
4. **Comprehensive Coverage**: Analyzes thousands of data points to identify relevant achievements across multiple sources.
5. **Real-Time Insights**: Generates reports from current database state, providing up-to-date progress tracking.
6. **Quality Assurance**: AI-powered synthesis reduces human error and omissions in narrative construction.

### Downstream Impact
- **Donor Reporting**: Supports World Bank reporting requirements with evidence-based narratives
- **Strategic Planning**: Enables data-driven decision-making through comprehensive progress visibility
- **Knowledge Management**: Preserves institutional memory by documenting achievements systematically
- **Performance Monitoring**: Facilitates real-time tracking of indicator progress against targets
- **Stakeholder Communication**: Provides polished narratives for external communications and impact stories

---

## Summary

The AICCRA Reports Generator Service represents a sophisticated application of generative AI and semantic search technologies to automate evidence-based reporting. By combining structured data from MARLO-AICCRA with advanced language models and vector retrieval, the service transforms fragmented project information into coherent, professional narratives that meet donor reporting standards. The system's modular architecture—separating data ingestion, vectorization, retrieval, and generation—ensures scalability and maintainability while delivering significant value to AICCRA coordinators and stakeholders through time savings, consistency, and comprehensive evidence integration.
