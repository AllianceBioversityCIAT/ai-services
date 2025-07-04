# AICCRA Report Generator REST API

This document describes the REST API for the AICCRA Report Generator Service, which provides HTTP access to the AI chatbot functionality with AWS Bedrock integration.

## Quick Start

### 1. Start the API Server

```bash
cd ar-generator-service
python3 api_server.py
```

The server will start on `http://localhost:8000` by default.

### 2. Access API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

### 3. Test the API

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"indicator": "IPI 1.1", "year": 2024}'
```

## API Endpoints

### `POST /api/generate`

Generate an AICCRA report for the specified indicator and year.

**Request Body:**
```json
{
  "indicator": "IPI 1.1",
  "year": 2024
}
```

**Parameters:**
- `indicator` (string, required): Indicator name (e.g., "IPI 1.1", "PDO Indicator 1")
- `year` (integer, required): Year for report generation (2020-2030)

**Response (200 OK):**
```json
{
  "indicator": "IPI 1.1",
  "year": 2024,
  "content": "Generated report content...",
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

### `POST /api/chat`

Alias for `/api/generate` with the same functionality.

### `GET /`

Root endpoint providing API information.

### `GET /health`

Health check endpoint.

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# AWS Bedrock Configuration
AWS_ACCESS_KEY_ID_BR=your_aws_access_key
AWS_SECRET_ACCESS_KEY_BR=your_aws_secret_key
AWS_REGION=us-east-1

# Knowledge Base Configuration
KNOWLEDGE_BASE_ID=your_knowledge_base_id
```

### Server Configuration

The API server can be configured with command-line arguments:

```bash
python3 api_server.py --help
```

Options:
- `--host`: Host to bind to (default: 0.0.0.0)
- `--port`: Port to bind to (default: 8000)
- `--reload`: Enable auto-reload for development
- `--log-level`: Set log level (debug, info, warning, error, critical)

## Examples

### Python Example

```python
import requests

# Make API request
response = requests.post(
    "http://localhost:8000/api/generate",
    json={"indicator": "IPI 1.1", "year": 2024}
)

if response.status_code == 200:
    data = response.json()
    print(f"Report for {data['indicator']} ({data['year']}):")
    print(data['content'])
else:
    print(f"Error: {response.json()}")
```

### JavaScript Example

```javascript
fetch('http://localhost:8000/api/generate', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        indicator: 'IPI 1.1',
        year: 2024
    })
})
.then(response => response.json())
.then(data => {
    if (data.status === 'success') {
        console.log(`Report: ${data.content}`);
    } else {
        console.error(`Error: ${data.error}`);
    }
});
```

## Available Indicators

The API supports the following indicators:
- IPI 1.1, IPI 1.2, IPI 1.3, IPI 1.4
- IPI 2.1, IPI 2.2, IPI 2.3
- IPI 3.1, IPI 3.2, IPI 3.3, IPI 3.4
- PDO Indicator 1-5

## Error Handling

The API returns appropriate HTTP status codes:
- `200`: Success
- `400`: Bad Request (validation errors)
- `403`: Forbidden (access denied)
- `422`: Unprocessable Entity (validation errors)
- `500`: Internal Server Error

## Testing

Run the comprehensive test suite:

```bash
python3 test_comprehensive.py
```

## Security

- Configure CORS settings appropriately for production
- Use environment variables for sensitive configuration
- Implement authentication as needed for production deployment
- Follow AWS IAM best practices for service permissions