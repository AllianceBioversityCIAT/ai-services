# PRMS QA Service

🔍 **A REST API service that processes CGIAR result metadata for PRMS using language models (LLM) to improve titles, descriptions, and short names for better clarity and compliance with standards.**

## Overview

The PRMS QA Service is designed to enhance CGIAR result metadata by leveraging AWS Bedrock Claude to generate improved titles, descriptions, and short names. The service processes result metadata based on result type and level, applying specific formatting rules and guidelines to ensure consistency with CGIAR standards.

### Key Features

- 🔍 **LLM-powered QA** for PRMS documents using AWS Bedrock Claude
- 🤖 **Intelligent prompt generation** based on result type and level
- 📊 **Optional interaction tracking** via external service for analytics
- 📦 **Simple REST API** for PRMS metadata processing
- 🏥 **Health monitoring** and comprehensive error handling
- 🌐 **CORS support** for cross-origin requests
- 🌐 **Web scraping** for evidence enrichment from multiple sources (CGSpace, PDFs, web pages)

### Use Cases

- Enhance result metadata for non-specialist audiences
- Generate QA improvements based on result type and level (Output, Outcome, Impact)
- Ensure consistency with CGIAR reporting standards
- Track user interactions for analytics and improvement

## Tech Stack

- **FastAPI** - Modern Python web framework
- **AWS Bedrock (Claude)** - LLM for text generation
- **Python 3.13** - Programming language
- **Uvicorn** - ASGI server
- **Pydantic** - Data validation

## Project Structure

```
qa-service/
├── .env                           # Environment variables (create from template)
├── .python-version               # Python version specification
├── requirements.txt              # Python dependencies
├── pyproject.toml               # Project configuration
├── api_server.py                # Development server entry point
├── main.py                      # AWS Lambda entry point
├── README.md                    # This file
├── app/
│   ├── api/
│   │   ├── main.py             # FastAPI application
│   │   ├── routes.py           # API endpoints
│   │   └── models.py           # Pydantic models
│   ├── llm/
│   │   ├── mining.py           # Core LLM processing logic
│   │   ├── test_innovdev.json  # Test data for innovation development
│   │   └── test_kb.json        # Test data for knowledge base
│   ├── web_scraping/
│   │   ├── web_scraping.py     # Web scraping service for evidence extraction
│   │   ├── evidence_scraper.py # Evidence enrichment and context formatting
│   │   └── WEB_SCRAPING_DOCUMENTATION.md # Complete web scraping documentation
│   └── utils/
│       ├── config/
│       │   └── config_util.py  # Configuration management
│       ├── interactions/
│       │   └── interaction_client.py # External interaction tracking
│       ├── logger/
│       │   └── logger_util.py  # Logging utilities
│       ├── notification/
│       │   └── notification_service.py # Slack notifications
│       ├── prompt/
│       │   └── prompt.py       # Dynamic prompt generation
│       └── s3/
│           └── s3_util.py      # AWS S3 utilities
└── data/
    ├── logs/                   # Application logs
    └── evidence_downloads/     # Downloaded evidence files
```

## Setup and Installation

### Prerequisites

- Python 3.13
- AWS account with Bedrock access
- AWS credentials configured

### 1. Environment Setup

Create and activate a Python virtual environment:

```bash
# Create virtual environment
python3.13 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# Install Playwright browsers (required for web scraping)
playwright install chromium
```

### 3. Environment Configuration

Create a `.env` file in the project root with your AWS credentials:

```bash
# Copy the template and edit with your values
cp .env.template .env
```

Required environment variables:

```env
# AWS Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1

# Environment
IS_PROD=false

# Optional: Slack notifications
SLACK_WEBHOOK_URL=your_slack_webhook_url
```

### 4. Run the Development Server

```bash
# Start the development server
python api_server.py

# Or with custom options
python api_server.py --host 0.0.0.0 --port 8000 --reload --log-level debug
```

The server will start and be available at:
- **API Server**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Web Scraping Features

The service includes a comprehensive web scraping module that automatically extracts evidence content from multiple sources to enrich the LLM context.

### Supported Sources

- **CGSpace Handles** (`hdl.handle.net`, `cgspace.cgiar.org`) - Automatically downloads and extracts PDFs from CGSpace repositories
- **DOI Articles** (`doi.org`) - Extracts abstract and main content from scientific publications
- **SharePoint/OneDrive** - Downloads and processes shared PDFs and Excel files
- **Web Pages** - Intelligently scrapes main content from general websites
- **Direct PDFs** - Downloads and extracts text from PDF URLs

### Key Features

✅ **Automatic source detection** - No need to specify URL type  
✅ **Content validation** - Detects and filters authentication pages, errors, and invalid content  
✅ **Multi-format support** - PDF, Excel, and HTML extraction  
✅ **Robust error handling** - Continues processing even if some URLs fail  
✅ **Token-aware truncation** - Limits content to fit LLM context windows  
✅ **Complete logging** - Tracks entire process for debugging

### Quick Start

```python
import asyncio
from app.web_scraping.evidence_scraper import EvidenceEnhancer

async def enhance_with_evidence():
    enhancer = EvidenceEnhancer()
    
    evidence_urls = [
        "https://hdl.handle.net/10568/174072",
        "https://doi.org/10.1234/example",
        "https://www.cgiar.org/research/publication/...",
    ]
    
    result = await enhancer.enhance_prms_context(
        result_metadata={...},
        evidence_urls=evidence_urls,
        max_evidences=5
    )
    
    # Use result['formatted_context'] in your LLM prompt
    print(f"Valid evidences: {result['evidence_count']}")
    print(f"Formatted context: {result['formatted_context']}")

asyncio.run(enhance_with_evidence())
```

### Configuration

The `EvidenceEnhancer` supports customizable parameters:

```python
enhancer = EvidenceEnhancer(
    download_dir="./data/evidence_downloads"  # Directory for downloaded files
)

result = await enhancer.enhance_prms_context(
    result_metadata=metadata,
    evidence_urls=urls,
    max_evidences=5  # Maximum number of evidences to process
)

# Extract with token limits
evidence_contents = await enhancer.extract_evidence_content(
    evidence_urls=urls,
    max_content_tokens=10000  # Maximum tokens per evidence (default: 10,000)
)
```

### Module Files

The web scraping functionality is organized in the following files:

| File | Purpose |
|------|---------|
| [`app/web_scraping/web_scraping.py`](app/web_scraping/web_scraping.py) | Core scraping service - handles URL detection, content extraction from different sources (CGSpace, DOI, SharePoint, web pages), and content validation |
| [`app/web_scraping/evidence_scraper.py`](app/web_scraping/evidence_scraper.py) | Evidence enrichment coordinator - processes multiple evidence URLs, formats content for LLM context, and manages token limits |
| [`app/web_scraping/WEB_SCRAPING_DOCUMENTATION.md`](app/web_scraping/WEB_SCRAPING_DOCUMENTATION.md) | Complete technical documentation with architecture details, validation system, usage examples, and troubleshooting |

### For Complete Documentation

See [`app/web_scraping/WEB_SCRAPING_DOCUMENTATION.md`](app/web_scraping/WEB_SCRAPING_DOCUMENTATION.md) for:
- Detailed architecture and data flow
- Content validation system
- Technology stack and comparisons
- Advanced usage examples
- Troubleshooting guide
- Performance recommendations


## API Usage

### Endpoint: Process PRMS Result Metadata

**POST** `/api/prms-qa`

Processes CGIAR result metadata using LLM to improve titles, descriptions, and short names.

#### Request Body

```json
{
  "result_metadata": {
    "result_id": "8",
    "result_type_name": "Innovation Development",
    "result_level_id": 4,
    "result_level_name": "Output",
    "result_name": "Original Title",
    "result_description": "Original Description",
    "geographic_scope": ["Mexico", "Zambia"],
    "contributing_partners": ["CIMMYT", "Local Partner"]
  },
  "user_id": "user123"
}
```

#### Response

```json
{
  "time_taken": "1.23",
  "json_content": {
    "new_title": "Improved Title for Non-Specialist Audience",
    "new_description": "Enhanced description with clear context and CGIAR contributions...",
    "short_name": "Short Innovation Name"
  },
  "interaction_id": "abc123",
  "status": "success"
}
```

### Example cURL Request

```bash
curl -X POST "http://localhost:8000/api/prms-qa" \
     -H "Content-Type: application/json" \
     -d '{
       "result_metadata": {
         "result_id": "8",
         "result_type_name": "Innovation Development",
         "result_level_id": 4,
         "result_level_name": "Output",
         "result_name": "Biofortified maize variety with enhanced zinc content",
         "result_description": "A new maize variety developed through biotechnology"
       },
       "user_id": "user123"
     }'
```

## Supported Result Types

The service handles different result types with specific formatting rules:

### Result Types
- **Knowledge Product** - Research publications, reports, datasets
- **Innovation Development** - New technologies, tools, varieties
- **Capacity Sharing for Development** - Training, workshops, knowledge transfer
- **Policy Change** - Policy adoptions, regulatory changes
- **Innovation Use** - Adoption and scaling of innovations

### Result Levels
- **Output** - Direct products of research activities
- **Outcome** - Changes resulting from outputs
- **Impact** - Long-term effects and transformations

## Key Processing Features

### 1. Dynamic Prompt Generation
The service generates context-specific prompts based on:
- Result type and level
- Geographic scope
- Contributing partners
- Specific formatting guidelines for each category

### 2. Content Enhancement
- **Titles**: Made clear for non-specialist audiences (max 30 words)
- **Descriptions**: Detailed context with CGIAR contributions (max 150 words)
- **Short Names**: Concise identifiers for innovations (Innovation Development only)

### 3. Quality Standards
- Removes technical jargon and abbreviations
- Ensures geographic and partner information is included
- Maintains consistency with CGIAR reporting standards
- Provides clear value propositions

## Testing

### Health Check
```bash
curl http://localhost:8000/health
```

### API Information
```bash
curl http://localhost:8000/
```

### Test with Sample Data
The project includes test files in [`app/llm/`](app/llm/):
- [`test_innovdev.json`](app/llm/test_innovdev.json) - Innovation development example
- [`test_kb.json`](app/llm/test_kb.json) - Knowledge base example

## Development

### Running with Auto-reload
```bash
python api_server.py --reload --log-level debug
```

### Server Options
```bash
python api_server.py --help
```

Available options:
- `--host`: Host to bind (default: 0.0.0.0)
- `--port`: Port to bind (default: 8000)
- `--reload`: Enable auto-reload for development
- `--log-level`: Set logging level (debug, info, warning, error, critical)

## Deployment

### AWS Lambda
The service includes Lambda support via [`main.py`](main.py):

```python
from mangum import Mangum
from app.api.main import app

handler = Mangum(app)
```

### Docker (if needed)
```bash
# Build image
docker build -t prms-qa-service .

# Run container
docker run -p 8000:8000 --env-file .env prms-qa-service
```

## Monitoring and Logging

### Logs
- Console output for development
- Rotating file logs in `/tmp/logs/app.log`
- Structured logging with timestamps and context

### Health Monitoring
- Health endpoint at `/health`
- Exception handling with detailed error responses
- Optional Slack notifications for production alerts

### Interaction Tracking
- Optional user interaction tracking
- Integration with external analytics service
- Response time monitoring

## Configuration

### AWS Bedrock Model
- **Model**: `us.anthropic.claude-sonnet-4-20250514-v1:0`
- **Region**: `us-east-1`
- **Temperature**: `0.1` (low for consistency)
- **Max Tokens**: `2000`

### Logging
- **Location**: `/tmp/logs/` (Lambda) or `data/logs/` (local)
- **Rotation**: 5MB files, 5 backups
- **Level**: Configurable (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## Troubleshooting

### Common Issues

1. **AWS Credentials Error**
   - Ensure AWS credentials are properly configured in `.env`
   - Verify Bedrock access permissions

2. **Module Import Errors**
   - Check Python version (requires 3.13)
   - Ensure all dependencies are installed: `pip install -r requirements.txt`

3. **Port Already in Use**
   - Use different port: `python api_server.py --port 8001`
   - Kill existing process: `lsof -ti:8000 | xargs kill -9`

4. **Model Access Issues**
   - Verify AWS Bedrock service availability in your region
   - Check model permissions and quotas

### Debug Mode
```bash
python api_server.py --log-level debug --reload
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with appropriate tests
4. Submit a pull request

## License

MIT License - See LICENSE file for details.

## Support

For issues and questions:
- Check the [API documentation](http://localhost:8000/docs) when running
- Review logs in `data/logs/app.log`
- Verify AWS Bedrock service status
- Check environment variable configuration