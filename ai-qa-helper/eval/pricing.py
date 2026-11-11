"""Claude Haiku 5.5 prices for cost estimates and the run's budget guard.

Source: Anthropic model documentation (claude-api skill, Haiku 5.5 migration notes): USD per million
tokens, input 0.10 / output 0.50 when the prompt is 100K tokens or fewer, 0.50 / 2.50 above; cache
reads 0.1x input, 5-minute cache writes 1.25x input. ``BEDROCK_MULTIPLIER`` adds 10% for a regional
Bedrock endpoint, to stay conservative. Confirm the Bedrock price on the AWS pricing page before
approving a run.
"""

from dataclasses import dataclass

from app.llm.provider import LlmUsage

LONG_PROMPT_TOKENS = 100_000
BEDROCK_MULTIPLIER = 1.10


@dataclass(frozen=True)
class RateCard:
    input_per_mtok: float
    output_per_mtok: float


SHORT = RateCard(0.10, 0.50)
LONG = RateCard(0.50, 2.50)


def usd(u: LlmUsage, multiplier: float = BEDROCK_MULTIPLIER) -> float:
    prompt = u.input_tokens + u.cache_read_input_tokens + u.cache_creation_input_tokens
    card = LONG if prompt > LONG_PROMPT_TOKENS else SHORT
    cost = (
        u.input_tokens * card.input_per_mtok
        + u.cache_read_input_tokens * card.input_per_mtok * 0.1
        + u.cache_creation_input_tokens * card.input_per_mtok * 1.25
        + u.output_tokens * card.output_per_mtok
    ) / 1_000_000
    return cost * multiplier
