# AICCRA Annual Report Generator Service

An AI-powered service for generating comprehensive annual reports for AICCRA (Accelerating Impacts of CGIAR Climate Research for Africa). This service combines a chatbot interface with automated report generation capabilities, leveraging vector databases and Large Language Models to produce high-quality, data-driven reports.

---

## 🌟 Features

- **🤖 Interactive Chatbot**: Streamlit-based conversational interface for querying AICCRA data
- **📊 Automated Report Generation**: AI-generated reports for various performance indicators
- **🔍 Vector Search**: Integration with AWS Bedrock Knowledge Base and OpenSearch
- **📈 Multi-Indicator Support**: Handles both IPI (Intermediate Performance Indicators) and PDO (Project Development Objective) indicators
- **💾 Database Integration**: MySQL connectivity for retrieving structured data
- **🎯 Real-time Streaming**: Streaming responses for better user experience

---

## 🏗️ Architecture

The service consists of three main components:

### 1. Chatbot Interface (`chatbot_app.py`)
- Interactive Streamlit web application
- Two modes: Chatbot and Report Generator
- Real-time streaming responses
- User-friendly interface for data exploration

### 2. REST API Service (`app/api/`)
- FastAPI-based REST API with OpenAPI documentation
- HTTP endpoints for programmatic access
- Request/response validation with Pydantic models
- Comprehensive error handling and logging
- CORS support for web applications

### 3. Core Processing Engine
- **Vector Database Options** (choose one):
  - `app/llm/knowledge_base.py` - AWS Bedrock Knowledge Base integration
  - `app/llm/vectorize_os.py` - OpenSearch vector processing
  - `app/llm/vectorize_db.py` - Supabase vector processing
- **Prompt Engineering**: Custom prompts for report generation
- **Database Connectivity**: MySQL integration for data retrieval

---

## 🛠️ Technology Stack

- **Frontend**: Streamlit
- **REST API**: FastAPI, Uvicorn, Pydantic
- **AI/ML**: AWS Bedrock (Claude 3 Sonnet), LangChain
- **Vector Database**: OpenSearch, Supabase
- **Traditional Database**: MySQL
- **Cloud Services**: AWS S3, AWS Bedrock Knowledge Base
- **Data Processing**: Pandas, NumPy
- **Authentication**: AWS4Auth
- **Package Management**: uv

---

## 📋 Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- AWS account with Bedrock access
- MySQL database
- OpenSearch or Supabase instance

---

## 🚀 Installation

### 1. Install uv package manager
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Set up virtual environment
```bash
cd ar-generator-service
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies
```bash
uv pip install -r pyproject.toml
```

---

## ⚙️ Configuration

Create a `.env` file in the service root directory with the following variables:

```bash
# AWS Bedrock Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1

# AWS Bedrock Knowledge Base
KNOWLEDGE_BASE_ID=your_knowledge_base_id

# OpenSearch Configuration
OPENSEARCH_ENDPOINT=your_opensearch_endpoint
OPENSEARCH_AWS_ACCESS_KEY=your_opensearch_access_key
OPENSEARCH_AWS_SECRET_KEY=your_opensearch_secret_key

# MySQL Database
DB_HOST=your_mysql_host
DB_PORT=3306
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
DB_NAME=your_database_name

# Supabase (if using)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

---

## 🎯 Usage

### Running the Streamlit Application

```bash
streamlit run chatbot_app.py
```

The application will start on `http://localhost:8501` and provide two main modes:

#### 1. AICCRA Chatbot Mode
- Interactive Q&A interface
- Natural language queries about AICCRA data
- Real-time streaming responses
- Persistent conversation history

#### 2. AICCRA Report Generator Mode
- Select from available indicators:
  - IPI 1.1 through IPI 3.4
  - PDO Indicators 1-5
- Choose reporting year (2021-2025)
- Generate comprehensive reports with one click

### Running the REST API Server

The service now provides a REST API for programmatic access to the AI chatbot functionality:

```bash
python3 api_server.py
```

The API server will start on `http://localhost:8000` with the following endpoints:
- `POST /api/generate` - Generate AICCRA report
- `POST /api/chat` - Chat with AICCRA assistant (alias for /api/generate)
- `GET /docs` - Interactive API documentation
- `GET /health` - Health check endpoint

**Example API Usage:**
```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"indicator": "IPI 1.1", "year": 2024}'
```

For detailed API documentation, see [API_README.md](./API_README.md).

### Running CLI Mode

For direct indicator processing:

```bash
uv run python main.py
```

This will process the default indicator (IPI 1.1) and year (2025) as defined in `main.py`. 

**Vector Database Options:**
By default, the CLI mode uses AWS Bedrock Knowledge Base as the vector database. However, the service supports three vector database options:

1. **AWS Bedrock Knowledge Base** (default) - Uses `app/llm/knowledge_base.py`
2. **OpenSearch** - Uses `app/llm/vectorize_os.py` 
3. **Supabase** - Uses `app/llm/vectorize_db.py`

To switch between vector databases, modify the import and function call in `main.py`. 

---

## 📊 Supported Indicators

### Intermediate Performance Indicators (IPI)
- **IPI 1.1**: Climate information services
- **IPI 1.2**: Weather/climate data access
- **IPI 1.3**: Early warning systems
- **IPI 1.4**: Climate risk assessments
- **IPI 2.1**: Agricultural technologies
- **IPI 2.2**: Farming practices adoption
- **IPI 2.3**: Productivity improvements
- **IPI 3.1**: Institutional capacity
- **IPI 3.2**: Policy development
- **IPI 3.3**: Knowledge sharing
- **IPI 3.4**: Partnership building

### Project Development Objective (PDO) Indicators
- **PDO 1-5**: Various project outcome metrics

---

## 🗂️ Project Structure

```
ar-generator-service/
├── chatbot_app.py                 # Main Streamlit application
├── main.py                        # CLI entry point
├── api_server.py                  # REST API server entry point
├── pyproject.toml                 # Project dependencies
├── uv.lock                        # Dependency lock file
├── API_README.md                  # REST API documentation
├── .env.example                   # Environment variables template
├── *.jsonl                        # Training/reference data files
├── app/
│   ├── api/                       # REST API modules
│   │   ├── __init__.py            # API package initialization
│   │   ├── main.py                # FastAPI application
│   │   ├── models.py              # Pydantic request/response models
│   │   └── routes.py              # API endpoint routes
│   ├── llm/                       # LLM processing modules
│   │   ├── knowledge_base.py      # AWS Bedrock KB integration
│   │   ├── vectorize_db.py        # Supabase vector operations
│   │   └── vectorize_os.py        # OpenSearch vector operations
│   └── utils/                     # Utility modules
│       ├── config/                # Configuration management
│       ├── logger/                # Logging utilities
│       ├── prompts/               # Prompt templates
│       └── s3/                    # S3 integration
├── data/logs/                     # Application logs
├── db_conn/                       # Database connections
└── lakehouse_integration/         # Data warehouse integration
```

---

## 🔧 Development

### Key Components

1. **Vector Processing** (`app/llm/`):
   - Handles embedding generation and vector search
   - Integrates with multiple vector databases
   - Supports hybrid search capabilities

2. **Prompt Engineering** (`app/utils/prompts/`):
   - Custom prompts for report generation
   - Knowledge base query optimization
   - Context-aware response generation

3. **Database Integration** (`db_conn/`):
   - MySQL connectivity for structured data
   - Data loading and preprocessing utilities

### Adding New Indicators

1. Add the indicator to the list in `chatbot_app.py`
2. Update prompt templates in `app/utils/prompts/`
3. Ensure corresponding data exists in the knowledge base

### Customizing Prompts

Edit the prompt templates in `app/utils/prompts/`:
- `kb_generation_prompt.py`: Knowledge base queries
- `report_generation_prompt.py`: Report generation templates

---

## 📝 Logging

Logs are automatically generated in `data/logs/app.log` with information about:
- Application startup and shutdown
- Database connections
- API calls to AWS services
- Error handling and debugging information

---

## 🔒 Security

- AWS credentials are managed through environment variables
- Database connections use secure authentication
- API keys are never logged or exposed
- Follow AWS IAM best practices for service permissions

---

## 🐛 Troubleshooting

### Common Issues

1. **AWS Bedrock Access Denied**
   - Verify AWS credentials and region
   - Ensure Bedrock service is enabled in your AWS account
   - Check IAM permissions for Bedrock and Knowledge Base access

2. **Database Connection Errors**
   - Verify MySQL credentials and host accessibility
   - Check network connectivity and firewall settings
   - Ensure database exists and user has appropriate permissions

3. **Vector Database Issues**
   - Confirm OpenSearch/Supabase endpoints and credentials
   - Verify index exists and is properly configured
   - Check vector dimensions and embedding model compatibility

4. **Streamlit Performance Issues**
   - Consider reducing vector search result limits
   - Optimize database queries
   - Monitor memory usage during large report generation

---

## 📈 Performance Optimization

- **Caching**: Implement caching for frequent queries
- **Batch Processing**: Process multiple indicators in batches
- **Connection Pooling**: Use database connection pooling
- **Vector Index Optimization**: Tune vector search parameters

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-indicator`)
3. Make your changes
4. Add tests if applicable
5. Commit your changes (`git commit -m 'Add new indicator support'`)
6. Push to the branch (`git push origin feature/new-indicator`)
7. Create a Pull Request

---

## 🔄 Version History

- **v0.1.0**: Initial release with basic chatbot and report generation
- Features in development: Enhanced analytics, multi-language support, advanced visualization

---