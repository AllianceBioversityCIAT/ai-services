"""Test doubles: a scripted LlmProvider and a fake Anthropic client for the Bedrock adapter."""

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

from app.llm.provider import LlmUsage, SuggestionRequest, SuggestionResult

ZERO_USAGE = LlmUsage()


class FakeLlmProvider:
    """Returns queued results (or raises queued exceptions) in order."""

    def __init__(self) -> None:
        self.calls: list[SuggestionRequest[Any]] = []
        self._script: list[SuggestionResult[Any] | Exception] = []

    def enqueue(self, *items: SuggestionResult[Any] | Exception) -> "FakeLlmProvider":
        self._script.extend(items)
        return self

    def suggest(self, request: SuggestionRequest[Any]) -> SuggestionResult[Any]:
        self.calls.append(request)
        if not self._script:
            raise AssertionError("FakeLlmProvider: no scripted result left")
        nxt = self._script.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt


@dataclass
class FakeMessages:
    response: Any = None
    error: Exception | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


def fake_client(response: Any = None, error: Exception | None = None) -> SimpleNamespace:
    return SimpleNamespace(messages=FakeMessages(response=response, error=error))


def fake_message(text: str, stop_reason: str = "end_turn", model: str = "anthropic.claude-haiku-5-5") -> SimpleNamespace:
    return SimpleNamespace(
        model=model,
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="thinking", thinking="..."), SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=1200, output_tokens=300, cache_read_input_tokens=900, cache_creation_input_tokens=None),
    )
