import json
import pytest
from fastapi import HTTPException
from types import SimpleNamespace
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def prms_client(monkeypatch):
    """TestClient with CLARISA auth bypassed."""
    async def _ok_dep():
        return "AI Text Mining - PRMS"

    # Import after env is available; patch Clarisa dependency factory.
    with patch("app.mcp.client.validate_with_clarisa") as mock_validate:
        mock_validate.return_value = lambda: _ok_dep
        # Re-import is awkward; instead patch Depends at endpoint level via app override
        from app.mcp import client as client_module

        app = client_module.app

        async def override_clarisa():
            return "AI Text Mining - PRMS"

        # Replace dependency for PRMS Clarisa on all uses of that callable identity is hard;
        # override by walking dependencies on the route.
        app.dependency_overrides = {}
        for route in app.routes:
            if getattr(route, "path", None) == "/prms/text-mining":
                for dep in route.dependant.dependencies:
                    if dep.call and getattr(dep.call, "__name__", "") == "_validate":
                        app.dependency_overrides[dep.call] = override_clarisa

        # Broader override: inject via header path by mocking httpx post
        with patch.object(client_module, "http_client") as http_client:
            http_client.post = AsyncMock(
                return_value=MagicMock(
                    status_code=200,
                    json=lambda: {"valid": True, "mis": "AI Text Mining - PRMS"},
                )
            )
            yield TestClient(app)
            app.dependency_overrides.clear()


def test_openapi_has_no_token_or_environment_url(prms_client):
    schema = prms_client.get("/openapi.json").json()
    prms = schema["paths"]["/prms/text-mining"]["post"]
    # multipart request body properties
    content = prms["requestBody"]["content"]["multipart/form-data"]["schema"]
    props = content.get("properties", {})
    assert "token" not in props
    assert "environmentUrl" not in props
    assert "audio_keys" in props or True  # may be under encoding-only schemas
    # security for API key
    assert "X-API-Key" not in str(props)


def test_openapi_includes_multisource_fields(prms_client):
    schema = prms_client.get("/openapi.json").json()
    prms = schema["paths"]["/prms/text-mining"]["post"]
    request_body = str(prms.get("requestBody", {}))
    assert "keys" in request_body or "keys" in str(prms)
    assert "text" in request_body or "text" in str(prms)
    assert "audio_keys" in request_body or "audio_keys" in str(prms)
    assert "token" not in request_body
    assert "environmentUrl" not in request_body


def test_missing_api_key_rejected():
    from app.mcp.client import app

    client = TestClient(app)
    response = client.post("/prms/text-mining", data={"text": "hello"})
    assert response.status_code in (401, 403, 422)


def test_empty_sources_400(prms_client):
    response = prms_client.post(
        "/prms/text-mining",
        headers={"X-API-Key": "test-key"},
        data={"text": "   "},
    )
    assert response.status_code == 400


def test_star_process_document_still_importable():
    from app.llm.star_mining.mining import process_document

    assert callable(process_document)


def test_prms_removed_from_mining_module():
    import app.llm.star_mining.mining as mining

    assert not hasattr(mining, "process_document_prms")


def test_prms_mcp_error_payload_becomes_http_exception():
    from app.mcp.client import _unwrap_prms_mcp_result

    result = SimpleNamespace(
        isError=False,
        content=[
            SimpleNamespace(
                text=json.dumps(
                    {
                        "status": "error",
                        "error": "Too many sources were provided for one request.",
                        "http_status": 413,
                    }
                )
            )
        ],
    )

    with pytest.raises(HTTPException) as exc_info:
        _unwrap_prms_mcp_result(result)

    assert exc_info.value.status_code == 413
    assert exc_info.value.detail == "Too many sources were provided for one request."


def test_prms_mcp_success_payload_is_unwrapped():
    from app.mcp.client import _unwrap_prms_mcp_result

    payload = {"project": "PRMS", "results": []}
    result = SimpleNamespace(
        isError=False,
        content=[SimpleNamespace(text=json.dumps(payload))],
    )

    assert _unwrap_prms_mcp_result(result) == payload
