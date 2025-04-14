import json
import os
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
import boto3
import sys
from typing import AsyncGenerator

# Add the parent directory to sys.path to properly import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.mcp.client import app
from app.llm.mining import process_document, invoke_model
from app.middleware.auth_middleware import AuthMiddleware

# Configure pytest-asyncio
pytest_plugins = ["pytest_asyncio"]

# Configure asyncio fixture scope to avoid deprecation warnings
def pytest_configure(config):
    config.addinivalue_line(
        "asyncio_default_fixture_loop_scope", "function"
    )

# Create a TestClient with a custom base URL
client = TestClient(app)

# Mock credentials for testing
MOCK_CREDENTIALS = {
    "accessKeyId": "test-access-key",
    "secretAccessKey": "test-secret-key",
    "sessionToken": "test-session-token"
}

# Test data
TEST_BUCKET = "test-bucket"
TEST_KEY = "test-document.pdf"
TEST_PROMPT = "Extract key information from this document"

@pytest_asyncio.fixture
async def mock_auth_success():
    """Fixture to mock successful authentication"""
    with patch.object(AuthMiddleware, 'authenticate', new_callable=AsyncMock) as mock_auth:
        mock_auth.return_value = {
            "user": {
                "username": "test-user",
                "environment": "test-environment"
            }
        }
        yield mock_auth

@pytest.fixture
def mock_s3():
    """Fixture to mock S3 document reading"""
    with patch('app.utils.s3.s3_util.read_document_from_s3') as mock_read:
        mock_read.return_value = "This is a test document content for AI text mining."
        yield mock_read

@pytest.fixture
def mock_invoke_model():
    """Fixture to mock model invocation"""
    with patch('app.llm.mining.invoke_model') as mock_invoke:
        mock_invoke.return_value = json.dumps({
            "analysis": {
                "key_points": ["Test point 1", "Test point 2"],
                "summary": "This is a test summary"
            }
        })
        yield mock_invoke

@pytest.fixture
def mock_embedding():
    """Fixture to mock embedding generation"""
    with patch('app.llm.vectorize.get_embedding') as mock_embed:
        mock_embed.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]  # Simple mock embedding
        yield mock_embed

@pytest_asyncio.fixture
async def mock_process_document():
    """Fixture to mock the entire document processing"""
    with patch('app.mcp.server.process_with_llm') as mock_process:
        mock_process.return_value = {
            "content": "Test response",
            "time_taken": "1.23",
            "json_content": {
                "analysis": {
                    "key_points": ["Test point 1", "Test point 2"],
                    "summary": "This is a test summary"
                }
            }
        }
        yield mock_process

class MockClientSession:
    """Mock ClientSession for easier testing"""
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def initialize(self):
        pass

    async def call_tool(self, tool_name, arguments):
        return {
            "analysis": {
                "key_points": ["Test point 1", "Test point 2"],
                "summary": "This is a test summary"
            }
        }

@pytest_asyncio.fixture
async def mock_stdio_client():
    """Fixture to mock the MCP stdio client"""
    async def mock_client(*args, **kwargs):
        read_mock = AsyncMock()
        write_mock = AsyncMock()
        return read_mock, write_mock
    
    with patch('app.mcp.client.stdio_client', side_effect=mock_client) as mock:
        yield mock

@pytest_asyncio.fixture
async def mock_session():
    """Fixture to mock the MCP client session"""
    session_mock = MockClientSession()
    
    with patch('app.mcp.client.ClientSession', return_value=session_mock):
        yield session_mock

def test_app_initialization():
    """Test that the FastAPI app initializes correctly"""
    assert app is not None
    assert app.title == "FastAPI"  # Default title if not set

@pytest.mark.asyncio
async def test_process_endpoint_missing_parameters():
    """Test process endpoint with missing parameters"""
    response = client.post("/process", json={})
    assert response.status_code == 400
    assert "Missing" in response.json()["detail"]

@pytest.mark.asyncio
async def test_process_endpoint_success():
    """Test successful processing of a document through the API endpoint"""
    # Mocking the entire process function instead of using fixtures
    # This avoids potential issues with asyncio contexts
    with patch('app.mcp.client.stdio_client') as mock_stdio:
        # Set up the mock for stdio_client
        read_mock = AsyncMock()
        write_mock = AsyncMock()
        mock_stdio.return_value.__aenter__.return_value = (read_mock, write_mock)
        
        # Set up the mock for ClientSession
        session_mock = AsyncMock()
        session_mock.__aenter__.return_value = session_mock
        session_mock.call_tool.return_value = {
            "analysis": {
                "key_points": ["Test point 1", "Test point 2"],
                "summary": "This is a test summary"
            }
        }
        
        with patch('app.mcp.client.ClientSession', return_value=session_mock):
            response = client.post(
                "/process",
                json={
                    "bucketName": TEST_BUCKET,
                    "key": TEST_KEY,
                    "credentials": MOCK_CREDENTIALS,
                    "prompt": TEST_PROMPT
                }
            )
            
            assert response.status_code == 200
            # We won't assert on the exact response content as it's mocked
            assert response.json() is not None

@pytest.mark.asyncio
async def test_process_endpoint_server_error():
    """Test handling of server errors in the process endpoint"""
    with patch('app.mcp.client.stdio_client') as mock_stdio:
        # Set up the mock for stdio_client
        read_mock = AsyncMock()
        write_mock = AsyncMock()
        mock_stdio.return_value.__aenter__.return_value = (read_mock, write_mock)
        
        # Set up the mock for ClientSession
        session_mock = AsyncMock()
        session_mock.__aenter__.return_value = session_mock
        session_mock.call_tool.side_effect = Exception("Test error")
        
        with patch('app.mcp.client.ClientSession', return_value=session_mock):
            response = client.post(
                "/process",
                json={
                    "bucketName": TEST_BUCKET,
                    "key": TEST_KEY,
                    "credentials": MOCK_CREDENTIALS
                }
            )
            
            assert response.status_code == 500
            assert "Test error" in response.json()["detail"]

@pytest.mark.asyncio
async def test_document_processing_flow():
    """Test the full document processing flow with mocked components"""
    # Use multiple patch decorators to mock all dependencies
    with patch('app.llm.mining.read_document_from_s3', return_value="This is a test document content for AI text mining."), \
         patch('app.llm.vectorize.get_embedding', return_value=[0.1, 0.2, 0.3, 0.4, 0.5]), \
         patch('app.llm.mining.invoke_model', return_value=json.dumps({
             "analysis": {
                 "key_points": ["Test point 1", "Test point 2"],
                 "summary": "This is a test summary"
             }
         })), \
         patch('app.llm.vectorize.check_reference_exists', return_value=True), \
         patch('app.llm.vectorize.get_all_reference_data', return_value="Mock reference data"), \
         patch('app.llm.vectorize.get_relevant_chunk', return_value="Mock relevant chunk"), \
         patch('app.llm.vectorize.store_temp_embeddings') as mock_store, \
         patch('app.llm.vectorize.clear_lancedb'):
        
        # Mock the database and table name return value
        mock_db = MagicMock()
        mock_store.return_value = (mock_db, "temp_table")
        
        # Call the function we're testing
        result = process_document(TEST_BUCKET, TEST_KEY, TEST_PROMPT)
        
        # Check that the document was processed correctly
        assert result is not None
        assert "json_content" in result
        assert "time_taken" in result
        assert "analysis" in result["json_content"]
        assert "key_points" in result["json_content"]["analysis"]

@pytest.mark.asyncio
async def test_authentication_flow(mock_auth_success):
    """Test the authentication flow"""
    from app.mcp.server import authenticate
    
    result = await authenticate(
        MOCK_CREDENTIALS,
        TEST_KEY,
        TEST_BUCKET
    )
    
    assert result is not None
    assert "user" in result
    assert result["user"]["username"] == "test-user"
    mock_auth_success.assert_called_once()

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
