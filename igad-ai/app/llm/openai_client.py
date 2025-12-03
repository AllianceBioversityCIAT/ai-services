from openai import OpenAI
from app.utils.config.config_util import OPENAI
from app.utils.logger.logger_util import get_logger
from app.utils.prompts.prompt_1 import build_rfp_prompt

logger = get_logger()
OPENAI_API_KEY = OPENAI["api_key"]
DEFAULT_RFP_PROMPT = build_rfp_prompt()

def return_response():
    logger.info("🚀 Invoking OpenAI API...")
    client = OpenAI(
        api_key=OPENAI_API_KEY
    )

    response = client.responses.create(
        model="gpt-5",
        reasoning={"effort": "low"},
        input=DEFAULT_RFP_PROMPT,
        tools=[{
            "type": "file_search",
            "vector_store_ids": ["vs_6914b5e0e65c8191a635116afd7499ba"]
        }]
    )

    logger.info(f"🔍 OpenAI API response: {response.output_text}")

    return response.output_text

if __name__ == "__main__":
    return_response()