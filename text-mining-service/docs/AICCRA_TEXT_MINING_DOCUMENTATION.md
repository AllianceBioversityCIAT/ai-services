### AICCRA Text Mining Service - Technical Documentation

#### 1. Service Overview

##### Purpose
The AICCRA Text Mining Service is an AI-powered document analysis system designed to extract structured innovation-related information from agricultural and climate adaptation documents within the MARLO-AICCRA platform.

##### Main Use Cases
- **Innovation Development Extraction**: Automatically identify and extract innovation-related results from project documents, reports, and research outputs
- **Structured Data Generation**: Convert unstructured text into standardized, structured data following AICCRA's reporting framework
- **Geographical and Actor Analysis**: Identify innovation scope (global, regional, national, sub-national), stakeholders, and organizations involved
- **Readiness Assessment**: Evaluate innovation maturity levels based on the Scaling Readiness framework (0-9 scale)
- **Metadata Enrichment**: Extract keywords, contact persons, innovation types, and other contextual metadata

---

#### 2. Data Sources

##### Input Documents
The service processes documents from two primary sources:

**Cloud Storage (Amazon S3)**
- Documents stored in designated S3 buckets (`ai-services-ibd`)
- Organized under project-specific folders (`aiccra/text-mining/files/`)
- Supports multiple file formats

**Direct File Uploads**
- Users can upload documents directly through the web interface
- Files are temporarily stored in S3 for processing

##### Supported File Formats
- **PDF**: Research papers, reports, technical documents
- **Microsoft Word (.docx)**: Project documents, proposals
- **Microsoft Excel (.xlsx, .xls)**: Structured datasets with innovation records
- **PowerPoint (.pptx)**: Presentation-based information
- **Plain Text (.txt)**: Basic text documents

##### Reference Data
The service maintains reference datasets for geographical validation and mapping:
- **CLARISA Regions**: UN49 region codes for geographical classification
- **CLARISA Countries**: ISO Alpha-2 country codes and ISO 3166-2 subnational codes

---

#### 3. Data Collection & Ingestion

##### Document Retrieval
Documents are retrieved from S3 using AWS SDK (boto3), with file-type-specific parsers applied based on extension:
- PDF extraction using PyPDF2
- Word document parsing via python-docx
- Excel processing with pandas (row-level structuring)
- PowerPoint extraction using python-pptx

##### Excel-Specific Processing
For Excel files, the service applies advanced preprocessing:
- Removes empty rows and columns
- Eliminates duplicate records
- Converts each meaningful row into a structured text chunk (column: value format)
- Treats each row as an independent data point for AI analysis

##### Text Normalization
All document content undergoes normalization:
- Unicode handling for international characters
- Whitespace standardization
- Format-specific metadata preservation

---

#### 4. AI Processing Pipeline

The AICCRA service implements a multi-stage Retrieval-Augmented Generation (RAG) pipeline:

##### Stage 1: Text Chunking
Documents are divided into manageable segments:
- **Standard Documents**: Recursive character splitting with 8,000-character chunks and 1,500-character overlap
- **Excel Files**: Row-level chunking where each row becomes a discrete chunk
- Ensures context preservation across chunk boundaries

##### Stage 2: Vector Embedding Generation
Each text chunk is converted into a high-dimensional vector representation:
- **Model**: Amazon Titan Embed Text v2
- **Embedding Dimension**: 1,024 dimensions
- **Purpose**: Enables semantic similarity search and contextual retrieval

##### Stage 3: Vector Storage
Embeddings are stored in LanceDB, a lightweight vector database:
- **Temporary Tables**: Document-specific embeddings stored with unique identifiers
- **Reference Tables**: Persistent storage for CLARISA geographical data
- **Storage Location**: Local database (`/tmp/miningdb` in production)

##### Stage 4: Semantic Retrieval
The system performs targeted information retrieval:
- User prompt is converted to a query embedding
- Vector similarity search identifies the most relevant document chunks
- Reference data (regions, countries) is automatically included in context

##### Stage 5: LLM Analysis
Retrieved context is processed by a Large Language Model:
- **Model**: Claude 3.7 Sonnet (via AWS Bedrock)
- **Temperature**: 0.1 (low randomness for consistent extraction)
- **Max Tokens**: 5,000
- **Input Structure**: Combined prompt + reference data + relevant chunks

##### Stage 6: Structured Output Generation
The LLM generates JSON-formatted results conforming to AICCRA's innovation schema:
- Field validation and type checking
- Conditional field inclusion (only populated fields are returned)
- Geographic code mapping and validation

##### The Analysis Prompt

The service uses a comprehensive, structured prompt that guides the LLM to extract innovation information consistently:

**Prompt Components**
- **Indicator Definition**: Specifies "Innovation Development" as the target indicator with clear definitions and keywords
- **Field-by-Field Instructions**: Detailed extraction rules for each output field (title, description, geoscope, innovation type, etc.)
- **Validation Rules**: Predefined value sets for categorical fields (e.g., innovation nature, types, readiness levels)
- **Geographic Coding**: Instructions for UN49 region codes, ISO Alpha-2 country codes, and ISO 3166-2 subnational codes
- **Actor Classification**: Guidelines for identifying and categorizing individual actors and organizations
- **Output Format**: JSON schema with mandatory and optional fields, including examples

**Key Prompt Features**
- Over 280 lines of structured instructions
- Includes the complete Scaling Readiness Calculator (levels 0-9) for innovation maturity assessment
- Comprehensive organization type and subtype taxonomies (NGOs, research institutions, government entities, etc.)
- Gender and age classification rules for individual actors
- Explicit instructions to omit fields when information is not available (avoiding null values)

**Customization**
Users can modify the default prompt through the web interface to:
- Focus on specific types of innovations
- Extract additional custom fields
- Adapt extraction logic for specialized document types

---

#### 5. Models & AI Technologies

##### Embedding Model
**Amazon Titan Embed Text v2**
- Purpose: Convert text to semantic vectors for similarity search
- Vector size: 1,024 dimensions
- Optimized for multilingual and domain-specific content

##### Language Model
**Anthropic Claude 3.7 Sonnet**
- Purpose: Information extraction and structured data generation
- Access: AWS Bedrock (model ID: `us.anthropic.claude-3-7-sonnet-20250219-v1:0`)
- Configuration: Low temperature (0.1) for deterministic outputs
- Capabilities: Long context window, advanced reasoning, instruction following

##### Vector Database
**LanceDB**
- Purpose: Store and query embeddings for semantic search
- Features: Columnar storage, SQL-like filtering, efficient similarity search
- Implementation: Local file-based database with persistent reference tables

---

#### 6. Supporting Technologies & Architecture

##### Cloud Infrastructure
**Amazon Web Services (AWS)**
- **S3**: Document storage and retrieval
- **Bedrock**: Managed access to foundation models (Claude, Titan)
- **Lambda**: Serverless deployment (API endpoint: Lambda Function URL)

##### Backend Framework
**FastAPI**
- RESTful API architecture
- Endpoint: `/aiccra/text-mining`
- Request handling: Multipart form data (files + metadata)
- Authentication: Token-based validation

##### Data Processing Libraries
- **LangChain**: Text splitting utilities
- **Pandas**: Excel data manipulation
- **PyPDF2**: PDF text extraction
- **python-docx**: Word document parsing
- **python-pptx**: PowerPoint content extraction

##### Supporting Services
- **Interaction Tracking**: Records user requests, AI outputs, and performance metrics
- **CLARISA Integration**: Geographical reference data synchronization
- **Logging**: Structured logging for monitoring and debugging

---

#### 7. Front-End & User Interaction

##### User Interface Components
The web-based interface provides a streamlined analysis workflow:

**User Information Section**
- Email capture for interaction tracking
- URL parameter support for pre-filled user data
- Session identification

**Document Source Selection**
Users can choose between two modes:
- **Upload Mode**: Drag-and-drop or file browser for direct uploads
- **Cloud Storage Mode**: Browse and select files from S3 folders

**Analysis Configuration**
- **Default Mode**: Uses the standard AICCRA prompt optimized for innovation extraction
- **Custom Mode**: Users can modify the analysis prompt for specialized extraction needs

##### User Inputs
- User email (required for tracking)
- Document selection (upload or S3 path)
- Optional: Custom analysis prompt
- Optional: Additional S3 folder paths

##### Processing Flow
1. User selects document and submits for analysis
2. Loading indicator displays during processing
3. Progress feedback provided through UI updates

##### System Outputs
**Raw JSON Display**
- Complete structured extraction results
- Expandable/collapsible sections

**Processed Results View**
- Human-readable presentation of extracted innovations
- Organized by result with all metadata fields

**Interaction Tracking**
- Unique interaction ID returned for each analysis
- Linked to user email for future reference

---

#### 8. Outputs & Value

##### Structured Innovation Records
Each processed document produces zero or more innovation results with the following structure:

**Core Fields**
- **Title**: Full innovation name
- **Short Title**: Concise descriptor (≤10 words)
- **Description**: Comprehensive innovation summary
- **Keywords**: Searchable terms in lowercase

**Geographical Classification**
- **Geoscope Level**: Global, Regional, National, Sub-national, or TBD
- **Regions**: UN49 codes (if regional)
- **Countries**: ISO Alpha-2 codes with optional subnational areas (ISO 3166-2)

**Innovation Characteristics**
- **Nature**: Incremental, Radical, Disruptive, or Other
- **Type**: Technological, Capacity Development, Policy/Institutional, or Other
- **Readiness Level**: 0-9 scale based on Scaling Readiness framework

**Stakeholder Information**
- **Main Contact Person**: Alliance focal point
- **Anticipated Users**: Classification (TBD or Determined)
- **Individual Actors**: Names, types (farmers, researchers, etc.), gender-age demographics
- **Organizations**: Names, types (NGO, Research, Government, etc.), subtypes

##### Business Value

**Time Savings**
- Automated extraction replaces manual document review
- Processes multi-page documents in minutes
- Consistent extraction across large document collections

**Data Standardization**
- Ensures uniform structure across innovation records
- Facilitates database integration and reporting
- Reduces human error in data entry

**Enhanced Analysis Capabilities**
- Enables rapid identification of innovation patterns
- Supports geographical analysis and stakeholder mapping
- Provides readiness assessments for strategic planning

**Decision Support**
- Structured outputs feed directly into MARLO-AICCRA reporting
- Supports portfolio analysis and investment decisions
- Enables trend identification across climate adaptation innovations

**Scalability**
- Processes individual documents or batch collections
- Adapts to various document formats without manual intervention
- Maintains consistent quality across varying input types

---

#### Technical Specifications Summary

| Component | Technology |
|-----------|-----------|
| **Embedding Model** | Amazon Titan Embed Text v2 (1,024 dimensions) |
| **LLM** | Claude 3.7 Sonnet via AWS Bedrock |
| **Vector Database** | LanceDB (local file-based) |
| **API Framework** | FastAPI with Lambda deployment |
| **Storage** | Amazon S3 |
| **Chunking** | RecursiveCharacterTextSplitter (8,000 chars, 1,500 overlap) |
| **Supported Formats** | PDF, DOCX, XLSX, XLS, PPTX, TXT |
| **Authentication** | Token-based via middleware |
| **Deployment** | AWS Lambda Function URL |

---

*This documentation describes the AICCRA Text Mining Service as implemented in the text-mining-service repository, specifically covering the aiccra_mining module and associated user interface components.*
