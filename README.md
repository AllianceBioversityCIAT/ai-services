# AI Services

A comprehensive collection of AI-powered microservices for the CGIAR initiative, providing intelligent document processing, report generation, data analysis, and administrative capabilities.

## 🌟 Overview

This repository hosts multiple AI microservices designed to enhance CGIAR's research and reporting capabilities through advanced machine learning and natural language processing technologies. Each service operates independently while sharing common infrastructure patterns and best practices.

## 🏗️ Repository Structure

```
ai-services/
├── admin-module/                  # Next.js Admin Dashboard
├── ai-feedback-service/           # AI Feedback Collection Service
├── ar-generator-service/          # AICCRA Annual Report Generator
├── chatbot-service/               # AICCRA Conversational AI Chatbot
├── clarisa-agresso-service/       # Institution Mapping Service
├── fast-response-service/         # General-Purpose LLM Response Service
├── mapping-service/               # Staff & Institution Field Mapping Service
├── partner-request-support/       # Partner Institution Matching System
├── qa-service/                    # PRMS Metadata QA Service
└── text-mining-service/           # Document Processing Service
```

## 🚀 Available Services

### 🖥️ Admin Module ([`admin-module`](admin-module))
A Next.js-based administration dashboard for managing all AI services in the platform. Provides:
- Product and project management with DynamoDB backend
- User registration and role management
- Prompt management with access control
- Authenticated admin interface with session handling
- **Stack**: Next.js 15, TypeScript, Tailwind CSS, AWS DynamoDB

---

### 📝 AI Feedback Service ([`ai-feedback-service`](ai-feedback-service))
A service-agnostic feedback collection and analytics platform designed to gather and analyze user feedback across all AI services. Features:
- Cross-service feedback collection with flexible metadata
- Real-time performance monitoring and user satisfaction tracking
- Auto-registration of new AI services
- Secure storage on AWS S3 with future database migration support
- **Stack**: FastAPI, Python 3.13, AWS S3, AWS Lambda (Mangum)

---

### 📊 AR Generator Service ([`ar-generator-service`](ar-generator-service))
An AI-powered service for generating comprehensive annual reports for AICCRA (Accelerating Impacts of CGIAR Climate Research for Africa). Features include:
- Automated report generation using AWS Bedrock Claude 3.7 Sonnet
- Support for multiple performance indicators (IPI and PDO)
- Vector database integration with OpenSearch
- RESTful API with FastAPI
- **Stack**: FastAPI, Python 3.13, AWS Bedrock, OpenSearch, AWS Lambda

---

### 💬 Chatbot Service ([`chatbot-service`](chatbot-service))
An intelligent conversational AI service for exploring AICCRA data and insights through natural language. Key capabilities:
- AWS Bedrock Agents with persistent memory across sessions
- Smart filtering by phase, indicator, and section
- Rich citations linking to relevant documents and reports
- Both REST API and Streamlit web interface
- SQL Server / Microsoft Fabric Lakehouse integration
- **Stack**: FastAPI, Streamlit, AWS Bedrock Agents, OpenSearch, SQL Server, AWS Lambda

---

### 🔗 CLARISA-Agresso Service ([`clarisa-agresso-service`](clarisa-agresso-service))
Institution mapping service that provides automated matching between Agresso and CLARISA institution databases. Features:
- Vector-based semantic matching using AWS Bedrock embeddings
- Support for multiple matching approaches (Supabase and OpenSearch)
- Batch processing capabilities
- Excel report generation
- **Stack**: FastAPI, Python 3.13, AWS Bedrock, OpenSearch, Supabase

---

### ⚡ Fast Response Service ([`fast-response-service`](fast-response-service))
A lightweight, general-purpose microservice that accepts any prompt and input text and returns an LLM-generated response. Ideal for:
- Text summarization and rewriting
- Writing improvement and style adaptation
- Contextual automatic response generation
- Any prompt-based text transformation task
- **Stack**: FastAPI, Python 3.13, AWS Bedrock Claude, AWS Lambda (Mangum)

---

### 🗂️ Mapping Service ([`mapping-service`](mapping-service))
A semantic field-mapping service that resolves free-text staff names and institution names to their canonical CLARISA/system IDs using vector search. Features:
- Supports `staff` and `institution` entity types
- OpenSearch-powered semantic matching
- Environment-aware routing (test/prod)
- **Stack**: FastAPI, Python 3.13, OpenSearch, AWS Lambda (Mangum)

---

### 🤝 Partner Request Support ([`partner-request-support`](partner-request-support))
A full-stack enterprise platform for validating and matching partner institution requests against the CLARISA database using hybrid AI search. Features:
- Hybrid search combining AI semantic embeddings + fuzzy string matching + multilingual support
- Excel file upload and direct CLARISA API integration
- Automated web research fallback for unmatched institutions
- Full approval workflow (accept/reject) with justification notes
- Color-coded match quality dashboard (Excellent / Good / Fair / No Match)
- **Stack**: FastAPI (backend), React/Next.js (frontend), AWS Bedrock, CLARISA API

---

### 🔍 QA Service ([`qa-service`](qa-service))
An LLM-powered quality assurance service for PRMS (Performance and Results Management System) result metadata. Key features:
- Generates improved titles, descriptions, and short names using AWS Bedrock Claude
- Intelligent prompt generation based on result type and level (Output, Outcome, Impact)
- Optional interaction tracking for analytics
- Slack notifications for processing events
- **Stack**: FastAPI, Python 3.13, AWS Bedrock Claude, AWS S3, AWS Lambda

---

### 🔎 Text Mining Service ([`text-mining-service`](text-mining-service))
Intelligent document processing microservice that extracts structured information from various document formats. Key capabilities:
- Document ingestion from S3 buckets
- Semantic chunking and vector embeddings with LanceDB
- AI-powered content analysis using Claude 3 Sonnet
- Authentication via CLARISA credentials
- Slack notifications for processing status
- **Stack**: FastAPI, Python 3.13, AWS Bedrock, LanceDB, AWS S3

---

## 🛠️ Common Technology Stack

| Category | Technologies |
|---|---|
| **AI/ML** | AWS Bedrock, Claude 3.7 Sonnet, OpenAI API, Vector Embeddings |
| **Databases** | OpenSearch, LanceDB, Supabase, MySQL, SQL Server, AWS DynamoDB |
| **Cloud** | AWS S3, AWS Bedrock Knowledge Base, AWS Lambda |
| **APIs** | FastAPI, Next.js API Routes, RESTful services |
| **Frontend** | Next.js 15, React, Tailwind CSS, Streamlit |
| **Data Processing** | Pandas, NumPy, Pydantic |
| **Package Management** | uv (Python), pnpm (Node.js) |
| **Authentication** | AWS IAM, CLARISA integration, NextAuth |
| **Deployment** | AWS Lambda via Mangum, Docker |

## 📋 Prerequisites

- Python 3.13+ (backend services)
- Node.js 20+ / pnpm (admin-module, partner-request-support frontend)
- [uv](https://github.com/astral-sh/uv) package manager
- AWS account with Bedrock access
- Appropriate database connections (varies by service)

## 🚀 Quick Start

Each service can be run independently. Navigate to the specific service directory and follow its individual README for detailed setup instructions:

```bash
# Example: Running a Python service
cd fast-response-service
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
python api_server.py

# Example: Running the admin module
cd admin-module
pnpm install
pnpm dev
```

## 🔒 Security & Configuration

All services follow consistent security practices:
- Environment variable configuration (`.env` files, never committed)
- AWS IAM-based authentication
- Secure API endpoints with proper validation
- No hardcoded credentials or sensitive data

## 🤝 Contributing

Each service accepts contributions independently. Please:

1. Navigate to the specific service directory
2. Follow the individual service's contribution guidelines
3. Create feature branches for new functionality
4. Ensure proper testing and documentation
5. Submit pull requests with clear descriptions

## 📊 Monitoring & Logging

All services implement comprehensive logging:
- Structured logging with rotating file handlers
- Console and file output
- Error tracking and debugging information
- Performance monitoring capabilities

## 📞 Support

For service-specific issues, refer to individual service documentation. For general repository questions or new service proposals, please open an issue in this repository.

---

**IBD AI Services** - Empowering agricultural research through artificial intelligence.