# AI Services Feedback API

![Python](https://img.shields.io/badge/python-3.13+-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-red.svg)
![AWS](https://img.shields.io/badge/AWS-S3%20%7C%20Lambda-orange.svg)

🔄 **AI Feedback Collection System**

A comprehensive feedback management service for collecting, storing, and analyzing user feedback on AI-generated responses across multiple AI services and applications.

## 🎯 **Overview**

This service provides a **feedback collection platform** designed to work with any AI service that generates user-facing content. Originally built for chatbot feedback, it has been restructured to support multiple AI services while maintaining backward compatibility.

### **Key Features**

- 📝 **Feedback Collection**: Works with any AI service
- 🔍 **Advanced Analytics**: Service-specific and cross-service insights  
- 📊 **Real-time Monitoring**: Track AI service performance and user satisfaction
- 🏗️ **Flexible Architecture**: Service-agnostic design for easy integration
- 🔒 **Secure Storage**: AWS S3 with future database migration support
- 📈 **Scalable Design**: Built to handle feedback from multiple services
- 🎛️ **Rich Context Support**: Flexible metadata for service-specific insights
- 🔄 **Auto-Registration**: Automatically discovers and registers new AI services

## 🚀 **Quick Start**

### **Prerequisites**

- Python 3.13+
- AWS Account with S3 access
- Environment variables configured

### **Installation**

```bash
# Clone the repository
git clone <repository-url>
cd ai-feedback-service

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your AWS credentials
```

### **Environment Configuration**

```bash
# .env file
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
BUCKET_NAME=your_bucket_name_here
```

### **Running the Service**

```bash
# Development server with auto-reload
python api_server.py --reload

# Production server
python api_server.py --host 0.0.0.0 --port 8001

# AWS Lambda deployment
# Uses main.py as the Lambda handler
```

### **Testing the API**

```bash
# Health check
curl http://localhost:8001/health

# API documentation
open http://localhost:8001/docs
```

## 📊 **Supported AI Services**

### **Currently Registered Services**

| Service | Description | Context Fields | Status |
|---------|-------------|----------------|--------|
| `chatbot` | Conversational AI interactions | `filters_applied` | ✅ Active |

### **Adding New Services**

New AI services are **automatically registered** when first encountered, or you can manually register them:

```python
# Automatic registration (first feedback submission)
POST /api/feedback
{
    "service_name": "my-new-service",
    "user_id": "user@example.com",
    "ai_output": "AI response...",
    "feedback_type": "positive"
}

# Manual registration (recommended for better analytics)
POST /api/feedback/services/register
{
    "service_name": "reports-generator",
    "display_name": "AICCRA Reports Generator",
    "description": "AI-powered report generation service",
    "expected_context": ["report_type", "data_sources"]
}
```

## 🔧 **API Endpoints**

### **Core Feedback Endpoints**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/feedback` | Submit feedback for any AI service |
| `GET` | `/api/feedback/summary` | Get cross-service analytics summary |
| `POST` | `/api/feedback/search` | Advanced feedback search and filtering |
| `GET` | `/api/feedback/services` | Get registered AI services information |
| `GET` | `/api/feedback/service/{service_name}` | Get service-specific feedback |

### **Service Management**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/feedback/services/register` | Register a new AI service |
| `GET` | `/health` | Service health check |
| `GET` | `/` | API information and integration guide |

### **Documentation**

| Endpoint | Description |
|----------|-------------|
| `/docs` | Interactive Swagger UI documentation |
| `/redoc` | ReDoc documentation |

## 💻 **Integration Examples**

### **Basic Feedback Submission**

```python
import requests

# Submit feedback for any AI service
response = requests.post('http://localhost:8001/api/feedback', json={
    'user_id': 'user@example.com',
    'session_id': 'session-123',
    'user_input': 'What is the weather like today?',
    'ai_output': 'Today is sunny with 22°C in your location.',
    'feedback_type': 'positive',
    'feedback_comment': 'Very accurate and helpful response!',
    'service_name': 'chatbot',
    'context': {
        'filters_applied': {'location': 'detected', 'source': 'weather_api'}
    },
    'response_time_seconds': 2.5,
    'platform': 'AICCRA'
})

print(response.json())
# {
#   "feedback_id": "fb_550e8400-e29b-41d4-a716-446655440000",
#   "status": "success",
#   "message": "Feedback submitted successfully...",
#   "timestamp": "2025-01-27T10:30:00Z",
#   "service_name": "chatbot"
# }
```

### **JavaScript/React Integration**

```javascript
class AIFeedbackService {
    constructor(apiUrl) {
        this.apiUrl = apiUrl;
    }
    
    async submitFeedback(feedbackData) {
        const response = await fetch(`${this.apiUrl}/api/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(feedbackData)
        });
        return response.json();
    }
    
    async getServiceAnalytics(serviceName) {
        const response = await fetch(
            `${this.apiUrl}/api/feedback/summary?service_name=${serviceName}`
        );
        return response.json();
    }
}

// React component example
const FeedbackButton = ({ aiInteraction }) => {
    const feedbackService = new AIFeedbackService('/api');
    
    const submitFeedback = async (type) => {
        await feedbackService.submitFeedback({
            feedback_type: type,
            service_name: aiInteraction.serviceName,
            user_id: currentUser.id,
            user_input: aiInteraction.userInput,
            ai_output: aiInteraction.aiOutput,
            context: aiInteraction.context,
            session_id: currentSession.id
        });
    };
    
    return (
        <div>
            <button onClick={() => submitFeedback('positive')}>👍</button>
            <button onClick={() => submitFeedback('negative')}>👎</button>
        </div>
    );
};
```

### **Service-Specific Examples**

#### **Chatbot Service**

```python
# Chatbot feedback with conversation context
requests.post('/api/feedback', json={
    'service_name': 'chatbot',
    'user_id': 'researcher@cgiar.org',
    'session_id': 'chat-session-456',
    'user_input': 'What progress has been made on IPI 1.1?',
    'ai_output': 'AICCRA has achieved significant progress on IPI 1.1...',
    'feedback_type': 'positive',
    'context': {
        'filters_applied': {
            'phase': 'Progress 2025',
            'indicator': 'IPI 1.1',
            'section': 'All sections'
        }
    },
    'response_time_seconds': 3.2
})
```

#### **Report Generator Service**

```python
# Report generation feedback
requests.post('/api/feedback', json={
    'service_name': 'reports-generator',
    'user_id': 'analyst@company.com',
    'user_input': 'Generate Q4 financial report for ACME Corp',
    'ai_output': '[Generated 50-page PDF report content]',
    'feedback_type': 'negative',
    'feedback_comment': 'Report missing key financial metrics',
    'context': {
        'report_type': 'quarterly_financial',
        'data_sources': ['erp_system', 'crm_data'],
        'template_used': 'standard_template_v2',
        'generation_time_seconds': 120
    },
    'response_time_seconds': 120.5
})
```

## 📊 **Analytics & Monitoring**

### **Getting Service Analytics**

```python
# Get overall feedback summary
summary = requests.get('/api/feedback/summary').json()

# Get service-specific summary
chatbot_summary = requests.get('/api/feedback/summary?service_name=chatbot').json()

# Get detailed feedback for a service
feedback_data = requests.get('/api/feedback/service/chatbot?limit=100').json()
```

### **Advanced Search**

```python
# Search with filters
search_request = {
    'service_name': 'chatbot',
    'feedback_type': 'negative',
    'has_comment': True,
    'start_date': '2025-01-01T00:00:00Z',
    'end_date': '2025-01-31T23:59:59Z',
    'limit': 50,
    'sort_by': 'timestamp',
    'sort_order': 'desc'
}

results = requests.post('/api/feedback/search', json=search_request).json()
```

## 🏗️ **Architecture**

### **Current Implementation**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   AI Services   │    │  Feedback API    │    │   AWS S3        │
│                 │───▶│                  │───▶│                 │
│ • Chatbot       │    │ • FastAPI        │    │ • Organized     │
│ • Reports Gen   │    │ • Pydantic       │    │   Structure     │
│ • Text Mining   │    │ • Auto-register  │    │ • Secure        │
│ • Custom        │    │ • Analytics      │    │   Storage       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### **Data Storage Structure**

```
S3 Bucket: ai-services-ibd/
├── ai-feedback/
│   ├── chatbot/
│   │   ├── 20250127/
│   │   │   ├── feedback_chatbot_20250127_143022_fb_abc123.json
│   │   │   └── feedback_chatbot_20250127_143145_fb_def456.json
│   │   └── 20250128/
│   ├── reports-generator/
│   │   └── 20250127/
│   └── text-mining/
│       └── 20250127/
```

### **Technology Stack**

| Component | Technology | Purpose |
|-----------|------------|---------|
| **API Framework** | FastAPI + Pydantic | High-performance API with validation |
| **Storage** | AWS S3 | Secure, scalable feedback storage |
| **Deployment** | AWS Lambda + Mangum | Serverless deployment option |
| **Logging** | Python logging | Comprehensive operation tracking |
| **Documentation** | OpenAPI/Swagger | Interactive API documentation |

## 📋 **Data Models**

### **Feedback Request**

```python
{
    "user_id": "string",                    # Required: User identifier
    "session_id": "string",                 # Optional: Session ID
    "user_input": "string",                 # Optional: Original user input
    "ai_output": "string",                  # Required: AI response
    "feedback_type": "positive|negative",   # Required: Feedback type
    "feedback_comment": "string",           # Optional: Detailed comment
    "service_name": "string",               # Required: AI service name
    "context": {},                          # Optional: Service-specific context
    "response_time_seconds": 2.5,           # Optional: Performance metric
    "platform": "string"                   # Optional: Platform identifier
}
```

### **Stored Feedback Record**

```json
{
    "feedback_id": "fb_550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-01-27T10:30:00.123456+00:00",
    "feedback_type": "positive",
    "feedback_comment": "Great response!",
    "has_comment": true,
    "user_id": "user@example.com",
    "session_id": "session-123",
    "platform": "AICCRA",
    "service_name": "chatbot",
    "service_display_name": "AICCRA Chatbot",
    "service_description": "Conversational AI for AICCRA data exploration",
    "user_input": "What is the weather?",
    "ai_output": "Today is sunny with 22°C...",
    "input_length": 19,
    "output_length": 156,
    "response_time_seconds": 2.5,
    "context": {
        "filters_applied": {"location": "detected"}
    },
    "metadata": {
        "comment_length": 15,
        "has_session": true,
        "has_performance_data": true,
        "context_fields": ["filters_applied"]
    }
}
```

## 🔒 **Security & Privacy**

### **Data Security**

- **Encrypted Storage**: All feedback data is encrypted in AWS S3
- **Access Control**: IAM-based access control for AWS resources
- **Secure Transmission**: HTTPS/TLS for all API communications
- **Input Validation**: Strict Pydantic model validation

### **Privacy Considerations**

- **User Identification**: Supports email, session ID, or anonymous tokens
- **Data Retention**: Configurable retention policies (future enhancement)
- **Content Privacy**: AI output content can be excluded for sensitive applications
- **Audit Trails**: Complete logging for compliance and monitoring

### **Configuration Security**

```bash
# Environment variables (never commit to code)
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here
BUCKET_NAME=your_bucket_name
```

## 📈 **Monitoring & Observability**

### **Health Monitoring**

```bash
# Health check endpoint
curl http://localhost:8001/health

# Response includes:
# - Service status
# - Registered services count
# - System capabilities
# - Performance metrics
```

### **Logging**

The service provides comprehensive logging:

```python
# Log locations
data/logs/app.log          # Rotating file logs
stdout                     # Console logs (development)

# Log levels
DEBUG    # Detailed operation information
INFO     # General operation status
WARNING  # Non-critical issues
ERROR    # Error conditions
```

### **Performance Metrics**

- **Feedback Submission**: < 1 second
- **Analytics Generation**: < 3 seconds  
- **Search Queries**: < 2 seconds
- **Service Registration**: < 500ms

## 🚀 **Deployment**

### **Local Development**

```bash
# Start development server
python api_server.py --reload --port 8001

# Run with custom configuration
python api_server.py --host 0.0.0.0 --port 8080 --log-level debug
```

### **AWS Lambda Deployment**

```python
# main.py serves as the Lambda handler
from mangum import Mangum
from app.api.main import app

handler = Mangum(app)
```

### **Docker Deployment** (Future Enhancement)

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8001
CMD ["python", "api_server.py", "--host", "0.0.0.0", "--port", "8001"]
```

## 🛠️ **Development**

### **Project Structure**

```
ai-feedback-service/
├── app/
│   ├── api/
│   │   ├── __init__.py          # API module initialization
│   │   ├── main.py              # FastAPI application
│   │   ├── models.py            # Pydantic models
│   │   └── routes.py            # API endpoints
│   └── utils/
│       ├── config/
│       │   └── config_util.py   # Configuration management
│       ├── feedback/
│       │   └── feedback_util.py # Core feedback service
│       ├── logger/
│       │   └── logger_util.py   # Logging configuration
│       └── s3/
│           └── upload_file_to_s3.py # S3 integration
├── data/
│   └── logs/                    # Application logs
├── main.py                      # Lambda entry point
├── api_server.py               # Development server
├── requirements.txt            # Python dependencies
├── pyproject.toml             # Project configuration
├── .env.example               # Environment template
└── README.md                  # This file
```

### **Adding New Features**

1. **New AI Service Support**: Services auto-register, no code changes needed
2. **New Endpoints**: Add to [`app/api/routes.py`](app/api/routes.py)
3. **New Models**: Add to [`app/api/models.py`](app/api/models.py)
4. **New Analytics**: Extend [`app/utils/feedback/feedback_util.py`](app/utils/feedback/feedback_util.py)

### **Testing**

```bash
# Manual testing via Swagger UI
open http://localhost:8001/docs

# API testing with curl
curl -X POST http://localhost:8001/api/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test@example.com",
    "ai_output": "Test response",
    "feedback_type": "positive",
    "service_name": "test-service"
  }'
```

## 🔮 **Future Enhancements**

### **Planned Features**

- **Database Migration**: Move from S3 to DynamoDB for better querying
- **Real-time Dashboards**: Live monitoring interfaces
- **Machine Learning Insights**: Automated feedback analysis
- **Webhook Support**: Real-time notifications
- **Multi-language Support**: International feedback collection
- **Advanced Analytics**: Trend analysis and predictive insights

### **Scalability Improvements**

- **Batch Processing**: Bulk feedback submission
- **Caching Layer**: Redis for frequently accessed data
- **API Rate Limiting**: Prevent abuse and ensure fair usage
- **Data Compression**: Optimize storage costs

## 🤝 **Contributing**

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/new-feature`
3. **Commit** changes: `git commit -am 'Add new feature'`
4. **Push** to branch: `git push origin feature/new-feature`
5. **Submit** a Pull Request

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 **Support**

- **Documentation**: [http://localhost:8001/docs](http://localhost:8001/docs)
- **Health Check**: [http://localhost:8001/health](http://localhost:8001/health)
- **Issues**: Submit via repository issue tracker

## 🏷️ **Version History**

- **v1.0.0** - AI feedback service
  - Multi-service support
  - Auto-registration
  - Comprehensive analytics
  - AWS S3 storage
  - FastAPI implementation

---

**Built with ❤️ by the CGIAR AI Services Team**

*Empowering AI improvement through comprehensive feedback collection*