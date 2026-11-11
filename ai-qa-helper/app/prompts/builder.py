"""Builds the model request for one (result, field, promptVersion).

v1 reproduces the previous helper's request (AI QA Assistant CSV generator + Prompt Batcher):
- system message ``"You are a helpful assistant."``;
- one user turn ``f"Context: {context}\\n\\n{prompt}"``, where ``context`` is
  ``JSON.stringify([{Content}, {Title}, {Result Description}], null, 2)`` with empty values left out,
  and ``prompt`` is the stored text verbatim. Single-brace placeholders such as ``{context}`` and
  ``{core_innovation}`` stay literal: that code only replaced ``{{column}}`` placeholders.
- ``Content`` (all evidence text of the result) capped at 32,767 characters, the Excel cell limit
  that bounded it in production.
Differences, all mechanical: no temperature (Haiku 5.5 rejects it), structured output with the same
keys plus ``Evidence Quote``, and scanned PDFs attached as document blocks (the previous pipeline had
no OCR and skipped them).

v2 puts the fixed rubric in the system prompt (cached) and the evidence first in the user turn, each
source tagged with its index so the quote can be traced, then the result's title and description.
The reported value is never sent to the model, to avoid anchoring.
"""

import json
from dataclasses import dataclass

from app.evidence.extractor import EvidenceSource
from app.llm.provider import ContentPart, Effort, PdfEvidence, SuggestionRequest, TextPart
from app.prompts.loader import PromptSpec

V1_SYSTEM = "You are a helpful assistant."
V1_CONTENT_CAP = 32_767
V2_TOTAL_EVIDENCE_CHARS = 120_000
"""Budget across all text sources (~30k tokens); later sources are cut first."""


@dataclass(frozen=True)
class ResultContext:
    title: str
    description: str


@dataclass(frozen=True)
class BuiltRequest:
    request: SuggestionRequest
    evidence_text: str
    """The evidence text actually sent, against which the quote is verified."""


def build_request(
    spec: PromptSpec,
    result: ResultContext,
    sources: list[EvidenceSource],
    effort: Effort,
    max_tokens: int,
) -> BuiltRequest:
    if spec.family == "v1":
        return _build_v1(spec, result, sources, effort, max_tokens)
    return _build_v2(spec, result, sources, effort, max_tokens)


def v1_context(title: str, description: str, content: str) -> str:
    """``JSON.stringify(arr, null, 2)``: same separators, non-ASCII kept as is."""
    pairs = [("Content", content), ("Title", title), ("Result Description", description)]
    return json.dumps([{k: v} for k, v in pairs if v], indent=2, ensure_ascii=False)


def _pdfs(sources: list[EvidenceSource]) -> list[ContentPart]:
    return [
        PdfEvidence(s.index, s.title or s.url, s.pdf_base64)
        for s in sources
        if s.status == "pdf_ocr" and s.pdf_base64
    ]


def _build_v1(spec, result, sources, effort, max_tokens) -> BuiltRequest:
    content = "\n\n".join(s.text for s in sources if s.status == "text" and s.text)[:V1_CONTENT_CAP]
    user = f"Context: {v1_context(result.title, result.description, content)}\n\n{spec.text}"
    request = SuggestionRequest(
        system=V1_SYSTEM,
        content=[*_pdfs(sources), TextPart(user)],
        output_model=spec.output_model,
        effort=effort,
        max_tokens=max_tokens,
        cache_system=False,
    )
    return BuiltRequest(request, content)


def _build_v2(spec, result, sources, effort, max_tokens) -> BuiltRequest:
    parts: list[ContentPart] = []
    sent: list[str] = []
    budget = V2_TOTAL_EVIDENCE_CHARS
    for s in sources:
        if s.status == "pdf_ocr" and s.pdf_base64:
            parts.append(PdfEvidence(s.index, s.title or s.url, s.pdf_base64))
        elif s.status == "text" and s.text and budget > 0:
            text = s.text[:budget]
            budget -= len(text)
            sent.append(text)
            body = text.replace("</evidence", "&lt;/evidence")
            parts.append(TextPart(f'<evidence index="{s.index}" source="{_attr(s.url)}">\n{body}\n</evidence>'))
    parts.append(
        TextPart(
            "<result>\n"
            f"<title>{_esc(result.title)}</title>\n"
            f"<description>{_esc(result.description)}</description>\n"
            "</result>\n\n"
            f"Assess the field \"{spec.label}\" for this result using the evidence above."
        )
    )
    request = SuggestionRequest(
        system=spec.text,
        content=parts,
        output_model=spec.output_model,
        effort=effort,
        max_tokens=max_tokens,
        cache_system=True,
    )
    return BuiltRequest(request, "\n\n".join(sent))


def _esc(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _attr(value: str) -> str:
    return _esc(value).replace('"', "&quot;")
