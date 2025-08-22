# AI Services

A comprehensive collection of AI-powered microservices for the CGIAR initiative, providing intelligent document processing, report generation, and data analysis capabilities.

## 🌟 Overview

This repository hosts multiple AI microservices designed to enhance CGIAR's research and reporting capabilities through advanced machine learning and natural language processing technologies. Each service operates independently while sharing common infrastructure patterns and best practices.

## 🏗️ Repository Structure

The repository is organized as a collection of independent microservices, each contained within its own directory:

```
ai-services/
├── ar-generator-service/          # AICCRA Annual Report Generator
├── clarisa-agresso-service/       # Institution Mapping Service  
├── text-mining-service/           # Document Processing Service
└── [future-services]/             # Additional AI services
```

## 🚀 Available Services

### 📊 AR Generator Service ([`ar-generator-service`](ar-generator-service ))
An AI-powered service for generating comprehensive annual reports for AICCRA (Accelerating Impacts of CGIAR Climate Research for Africa). Features include:
- Automated report generation using AWS Bedrock Claude 3.7 Sonnet
- Support for multiple performance indicators (IPI and PDO)
- Vector database integration with OpenSearch
- RESTful API with FastAPI

### 🔍 Text Mining Service ([`text-mining-service`](text-mining-service ))
Intelligent document processing microservice that extracts structured information from various document formats. Key capabilities:
- Document ingestion from S3 buckets
- Semantic chunking and vector embeddings with LanceDB
- AI-powered content analysis using Claude 3 Sonnet
- Authentication via CLARISA credentials
- Slack notifications for processing status

### 🔗 CLARISA-Agresso Service ([`clarisa-agresso-service`](clarisa-agresso-service ))
Institution mapping service that provides automated matching between Agresso and CLARISA institution databases. Features:
- Vector-based semantic matching using AWS Bedrock embeddings
- Support for multiple matching approaches (Supabase and OpenSearch)
- Batch processing capabilities
- Excel report generation

## 🛠️ Common Technology Stack

All services leverage modern AI and cloud technologies:

- **AI/ML**: AWS Bedrock, Claude 3.7 Sonnet, Vector Embeddings
- **Databases**: OpenSearch, Supabase, MySQL, SQL Server
- **Cloud Services**: AWS S3, AWS Bedrock Knowledge Base
- **APIs**: FastAPI, RESTful services
- **Data Processing**: Pandas, NumPy
- **Package Management**: uv
- **Authentication**: AWS IAM, CLARISA integration

## 📋 Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- AWS account with Bedrock access
- Appropriate database connections (varies by service)

## 🚀 Quick Start

Each service can be run independently. Navigate to the specific service directory and follow its individual README for detailed setup instructions:

```bash
# Example: Running the text mining service
cd text-mining-service
uv venv
source .venv/bin/activate
uv pip install -r pyproject.toml
uv run python main.py
```

## 🔒 Security & Configuration

All services follow consistent security practices:
- Environment variable configuration (`.env` files)
- AWS IAM-based authentication
- Secure API endpoints with proper validation
- No hardcoded credentials or sensitive data

## 🎯 Use Cases

- **Research Organizations**: Automate report generation and document analysis
- **Data Analysts**: Extract insights from large document collections  
- **Project Managers**: Generate performance reports and track indicators
- **Institutions**: Map and standardize organizational data across systems

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

## 🔮 Future Services

This repository will continue to expand with additional AI services for:
- Advanced analytics and visualization
- Multi-language document processing
- Real-time data streaming analysis
- Custom AI model training and deployment

## 📞 Support

For service-specific issues, refer to individual service documentation. For general repository questions or new service proposals, please open an issue in this repository.

---

**IBD AI Services** - Empowering agricultural research through artificial intelligence.