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
    prms_schema = str(prms)
    assert "token" not in prms_schema
    assert "environmentUrl" not in prms_schema
    assert "files" not in prms_schema


def test_openapi_includes_multisource_fields(prms_client):
    schema = prms_client.get("/openapi.json").json()
    prms = schema["paths"]["/prms/text-mining"]["post"]
    request_body = prms.get("requestBody", {})
    content = request_body.get("content", {})
    assert "application/json" in content
    assert "multipart/form-data" not in content

    prms_request_schema = schema["components"]["schemas"]["PrmsTextMiningRequest"]
    json_schema = str(prms_request_schema)
    assert "keys" in json_schema
    assert "text" in json_schema
    assert "audio_keys" in json_schema
    assert "bucketName" in json_schema
    assert "files" not in json_schema
    assert "token" not in json_schema
    assert "environmentUrl" not in json_schema


def test_missing_api_key_rejected():
    from app.mcp.client import app

    client = TestClient(app)
    response = client.post("/prms/text-mining", json={"text": "hello"})
    assert response.status_code in (401, 403, 422)


def test_empty_sources_400(prms_client):
    response = prms_client.post(
        "/prms/text-mining",
        headers={"X-API-Key": "test-key"},
        json={"text": "   "},
    )
    assert response.status_code == 400


def test_json_body_with_keys_and_bucket(prms_client):
    with patch("app.mcp.client.stdio_client") as mock_stdio:
        read = AsyncMock()
        write = AsyncMock()
        mock_stdio.return_value.__aenter__.return_value = (read, write)

        session = AsyncMock()
        session.initialize = AsyncMock()
        session.call_tool = AsyncMock(
            return_value=SimpleNamespace(
                isError=False,
                content=[SimpleNamespace(text='{"project": "PRMS", "results": []}')],
            )
        )

        with patch("app.mcp.client.ClientSession") as mock_session_cls:
            mock_session_cls.return_value.__aenter__.return_value = session
            response = prms_client.post(
                "/prms/text-mining",
                headers={"X-API-Key": "test-key"},
                json={
                    "bucketName": "ai-services-ibd",
                    "keys": ["prms/text-mining/files/test/report.pdf"],
                    "text": "optional context",
                    "user_id": "user@example.com",
                },
            )

    assert response.status_code == 200
    session.call_tool.assert_awaited_once()
    assert session.call_tool.await_args.kwargs["arguments"]["bucket"] == "ai-services-ibd"
    assert session.call_tool.await_args.kwargs["arguments"]["keys"] == [
        "prms/text-mining/files/test/report.pdf"
    ]


def test_star_process_document_still_importable():
    from app.text_mining.star_mining.mining import process_document

    assert callable(process_document)


def test_prms_removed_from_mining_module():
    import app.text_mining.star_mining.mining as mining

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
