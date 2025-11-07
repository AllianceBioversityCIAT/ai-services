# AICCRA AI Chatbot Service

An intelligent conversational AI service for exploring AICCRA (Accelerating Impacts of CGIAR Climate Research for Africa) data and insights. This service provides an interactive chatbot interface that can answer questions about AICCRA's activities, deliverables, innovations, and performance indicators using natural language processing and vector search capabilities.

---

## 🌟 Features

- **💬 Conversational Interface**: Natural language interaction with AICCRA data
- **🧠 Memory-Enabled**: Remembers conversation context across sessions
- **🔍 Smart Filtering**: Apply filters by phase, indicator, and section
- **📊 Data-Driven Insights**: Provides insights from real AICCRA reporting data
- **🎯 Contextual Responses**: Builds upon previous questions for comprehensive answers
- **🔗 Rich Citations**: Includes links to relevant documents and reports
- **🌐 Multi-Interface**: Both REST API and Streamlit web interface

---

## 🏗️ Architecture

The service consists of three main components:

### 1. REST API Service (`app/api/`)
- FastAPI-based REST API with OpenAPI documentation
- HTTP endpoints for programmatic access
- Request/response validation with Pydantic models
- Comprehensive error handling and logging
- CORS support for web applications

### 2. Streamlit Web Interface (`chatbot.py`)
- User-friendly web interface for direct interaction
- Session management and conversation history
- Dynamic filtering by phase, indicator, and section
- Export conversation functionality
- User feedback collection

### 3. Core AI Engine
- **AWS Bedrock Agents**: Advanced conversational AI with memory
- **Knowledge Base Integration**: AWS Bedrock Knowledge Base for vector search
- **Vector Processing**: OpenSearch integration for semantic search
- **Database Connectivity**: SQL Server integration for structured data

---

## 🛠️ Technology Stack

- **REST API**: FastAPI, Uvicorn, Pydantic
- **Web Interface**: Streamlit
- **AI/ML**: AWS Bedrock Agents (Claude 3.7 Sonnet) with session memory
- **Vector Database**: Amazon Bedrock Knowledge Base, OpenSearch
- **Traditional Database**: SQL Server (Microsoft Fabric)
- **Cloud Services**: AWS S3, AWS Bedrock, Amazon OpenSearch
- **Data Processing**: Pandas, NumPy
- **Authentication**: AWS4Auth
- **Package Management**: uv
- **Deployment**: Mangum (for AWS Lambda)

---

## 📋 Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- AWS account with Bedrock Agents and Knowledge Base access
- SQL Server database or Microsoft Fabric Lakehouse connection
- OpenSearch instance for vector search

---

## 🚀 Installation

### 1. Set up virtual environment
```bash
cd chatbot-service
python -m venv .venv/
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuration

Create a `.env` file in the service root directory with the following variables:

```bash
# AWS Bedrock Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID_BR=your_aws_access_key
AWS_SECRET_ACCESS_KEY_BR=your_aws_secret_key

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
BUCKET_NAME=your_bucket_name

# OpenSearch Configuration
AWS_ACCESS_KEY_ID_OS=your_opensearch_access_key
AWS_SECRET_ACCESS_KEY_OS=your_opensearch_secret_key
OPENSEARCH_HOST=your_opensearch_host
OPENSEARCH_INDEX_NAME_CHATBOT=your_index_name

# SQL Server Configuration (Microsoft Fabric)
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
SERVER=your_fabric_server_url
DATABASE=your_lakehouse_name

# Knowledge Base and Agents Configuration
KNOWLEDGE_BASE_ID=your_knowledge_base_id
AGENT_ID=your_agent_id
AGENT_ALIAS_ID=your_agent_alias_id
MEMORY_ID=your_memory_email
```

---

## 🎯 Usage

### 1. Start the Streamlit Web Interface

```bash
streamlit run chatbot.py
```

The web interface will be available at `http://localhost:8501`.

### 2. Start the REST API Server

```bash
python api_server.py
```

The API server will start on `http://localhost:8000` by default.

### 3. Access API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

### 4. Test the API

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What progress has been made on IPI 1.1 in 2025?",
    "phase": "Progress 2025",
    "indicator": "IPI 1.1",
    "section": "All sections",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "memory_id": "user@example.com"
  }'
```

---

## 📋 API Endpoints

### `POST /api/chat`

Send a message to the AICCRA AI chatbot and receive an intelligent response.

**Request Body:**
```json
{
  "message": "What progress has been made on IPI 1.1 in 2025?",
  "phase": "Progress 2025",
  "indicator": "IPI 1.1", 
  "section": "All sections",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "memory_id": "user@example.com"
}
```

**Parameters:**
- `message` (string, required): Your question or message to the chatbot
- `phase` (string, optional): Filter by reporting phase (default: "All phases")
- `indicator` (string, optional): Filter by performance indicator (default: "All indicators")
- `section` (string, optional): Filter by data section (default: "All sections")
- `session_id` (string, required): Unique session identifier for conversation continuity
- `memory_id` (string, required): User email address for personalized knowledge base access

**Response (200 OK):**
```json
{
  "message": "Based on the latest data, AICCRA has achieved significant progress on IPI 1.1 in 2025...",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "filters_applied": {
    "phase": "Progress 2025",
    "indicator": "IPI 1.1",
    "section": "All sections"
  },
  "status": "success"
}
```

**Error Response (400/500):**
```json
{
  "error": "Error message",
  "status": "error", 
  "details": "Additional error details"
}
```

### `GET /`

Root endpoint providing comprehensive API information.

### `GET /health`

Health check endpoint with service status.

---

## 🗣️ What You Can Ask

### Progress & Achievements
- "What progress has been made on IPI 1.1 in 2025?"
- "How are clusters performing against their targets?"
- "Show me achievements for PDO Indicator 3"

### Research & Deliverables
- "What publications were released by the Kenya cluster?"
- "Show me deliverables related to climate information services"
- "What research outputs are available for Theme 2?"

### Innovations & Technology
- "What innovations were developed for climate-smart agriculture?"
- "Show me tools created for early warning systems"
- "What is the readiness level of AICCRA innovations?"

### Impact & Outcomes
- "What real-world impacts has AICCRA achieved?"
- "Show me outcome case reports from Western Africa"
- "How has AICCRA contributed to farmer livelihoods?"

---

## 🔧 Filtering Options

Use filters to focus your queries:

- **Phase**: Target specific reporting periods
  - "All phases", "AWPB 2021-2025", "Progress 2021-2025", "AR 2021-2025"
- **Indicator**: Focus on specific performance indicators
  - "All indicators", "IPI 1.1-3.4", "PDO Indicator 1-5"
- **Section**: Limit to specific data types
  - "All sections", "Deliverables", "Contributions", "Innovations", "OICRs"

---

## 📊 Supported Data Types

### Performance Indicators
- **IPI 1.1-1.4**: Climate information and early warning systems
- **IPI 2.1-2.3**: Agricultural technologies and practices
- **IPI 3.1-3.4**: Institutional capacity and partnerships
- **PDO Indicator 1-5**: Project outcome and impact metrics

### Data Sections
- **Deliverables**: Research outputs, publications, tools, and datasets
- **Contributions**: Cluster activities, milestone progress, and narratives
- **Innovations**: Technology developments, platforms, and practices
- **OICRs**: Outcome Impact Case Reports documenting real-world impacts

### Reporting Phases
- **AWPB**: Annual Work Plan and Budget (planning phase)
- **Progress**: Mid-year progress reports
- **AR**: Annual Reports (achievements and outcomes)

---

## 🗂️ Project Structure

```
chatbot-service/
├── chatbot.py                     # Streamlit web interface
├── main.py                        # Lambda deployment entry point
├── api_server.py                  # REST API server entry point
├── pyproject.toml                 # Project dependencies
├── uv.lock                        # Dependency lock file
├── .env.example                   # Environment variables template
├── app/
│   ├── api/                       # REST API modules
│   │   ├── __init__.py            # API package initialization
│   │   ├── main.py                # FastAPI application
│   │   ├── models.py              # Pydantic request/response models
│   │   └── routes.py              # API endpoint routes
│   ├── llm/                       # AI/ML processing modules
│   │   ├── agents.py              # AWS Bedrock Agents integration
│   │   ├── invoke_llm.py          # Direct LLM invocation
│   │   ├── knowledge_base.py      # AWS Bedrock KB integration
│   │   └── vectorize_os.py        # OpenSearch vector operations
│   └── utils/                     # Utility modules
│       ├── agents_utils/          # Agent-specific utilities
│       ├── config/                # Configuration management
│       ├── logger/                # Logging utilities
│       ├── prompts/               # Prompt templates
│       └── s3/                    # S3 integration
├── data/logs/                     # Application logs
└── db_conn/                       # Database connections
```

---

## 💬 Example Usage

### Python Example

```python
import requests

# Make API request
response = requests.post(
    "http://localhost:8000/api/chat",
    json={
        "message": "What innovations were developed for climate-smart agriculture?",
        "phase": "All phases",
        "indicator": "All indicators", 
        "section": "Innovations",
        "session_id": "my-session-123",
        "memory_id": "researcher@cgiar.org"
    }
)

if response.status_code == 200:
    data = response.json()
    print(f"Chatbot Response: {data['message']}")
else:
    print(f"Error: {response.json()}")
```

### JavaScript Example

```javascript
fetch('http://localhost:8000/api/chat', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        message: 'Show me deliverables from the Western Africa cluster',
        phase: 'Progress 2025',
        indicator: 'All indicators',
        section: 'Deliverables',
        session_id: 'web-session-456',
        memory_id: 'user@example.com'
    })
})
.then(response => response.json())
.then(data => {
    if (data.status === 'success') {
        console.log(`Chatbot: ${data.message}`);
    } else {
        console.error(`Error: ${data.error}`);
    }
});
```

---

## ⚡ Performance Notes

- **Initial Response**: ~3-5 seconds for new sessions
- **Follow-up Questions**: ~2-3 seconds with conversation memory
- **Complex Queries**: May take longer for comprehensive analysis
- **Vector Search**: Optimized for semantic similarity matching
- **Session Memory**: Maintains context across conversation turns

---

## 🔧 Development

### Key Components

1. **AWS Bedrock Agents** ([`app/llm/agents.py`](app/llm/agents.py)):
   - Handles conversational AI with session memory
   - Integrates with AWS Bedrock Knowledge Base
   - Supports streaming responses and context retention

2. **Vector Search** ([`app/llm/vectorize_os.py`](app/llm/vectorize_os.py)):
   - OpenSearch integration for semantic search
   - Embedding generation and similarity matching
   - Dynamic filtering by metadata

3. **Prompt Engineering** ([`app/utils/prompts/`](app/utils/prompts/)):
   - Custom prompts for chatbot responses
   - Knowledge base query optimization
   - Context-aware response generation

4. **Database Integration** ([`db_conn/`](db_conn/)):
   - SQL Server connectivity for structured data
   - Data loading and preprocessing utilities
   - View creation for optimized queries

### Customizing Prompts

Edit the prompt templates in [`app/utils/prompts/`](app/utils/prompts/):
- [`chatbot_prompt.py`](app/utils/prompts/chatbot_prompt.py): Main chatbot response template
- [`kb_generation_prompt.py`](app/utils/prompts/kb_generation_prompt.py): Knowledge base prompt template

---

## 📝 Logging

Logs are automatically generated in [`data/logs/app.log`](data/logs/app.log) with information about:
- Chatbot conversations and responses
- AWS Bedrock Agents interactions
- Vector search operations
- Database connections and queries
- Error handling and debugging information

---

## 🔒 Security

- AWS credentials are managed through environment variables
- Session IDs provide conversation isolation
- User emails (memory_id) enable personalized access
- Database connections use secure authentication
- API keys are never logged or exposed
- Follow AWS IAM best practices for service permissions

---

## 🐛 Troubleshooting

### Common Issues

1. **AWS Bedrock Agents Access Denied**
   - Verify AWS credentials and region
   - Ensure Bedrock Agents service is enabled in your AWS account
   - Check IAM permissions for Bedrock Agents and Knowledge Base access

2. **Knowledge Base Not Found**
   - Verify `KNOWLEDGE_BASE_ID`, `AGENT_ID`, and `AGENT_ALIAS_ID`
   - Ensure Knowledge Base is properly configured and synchronized
   - Check vector index status in AWS console

3. **Database Connection Errors**
   - Verify SQL Server credentials and host accessibility
   - Check network connectivity and firewall settings
   - Ensure database exists and user has appropriate permissions

4. **Vector Search Issues**
   - Confirm OpenSearch endpoints and credentials
   - Verify index exists and is properly configured
   - Check vector dimensions and embedding model compatibility

5. **Session Memory Problems**
   - Ensure `memory_id` (user email) is valid and consistent
   - Check session ID format and uniqueness
   - Verify Bedrock Agents memory configuration

---

## 📈 Performance Optimization

- **Session Management**: Implement efficient session storage
- **Vector Search**: Optimize index parameters and query filters
- **Caching**: Cache frequent queries and responses
- **Connection Pooling**: Use database connection pooling
- **Memory Usage**: Monitor conversation memory limits

---

## 🚀 Deployment

### AWS Lambda Deployment

The service is configured for AWS Lambda deployment using Mangum:

```python
# main.py
from mangum import Mangum
from app.api.main import app

handler = Mangum(app)
```

### Docker Deployment

```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY . .

RUN pip install uv
RUN uv pip install -e .

EXPOSE 8000
CMD ["python", "api_server.py"]
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-capability`)
3. Make your changes
4. Add tests if applicable
5. Commit your changes (`git commit -m 'Add new chatbot capability'`)
6. Push to the branch (`git push origin feature/new-capability`)
7. Create a Pull Request

---

## 🔄 Version History

- **v1.0.0**: Initial release with AWS Bedrock Agents integration
- **Features**: Conversational AI, session memory, vector search, multi-interface support
- **In Development**: Enhanced analytics, multi-language support, advanced filtering

---