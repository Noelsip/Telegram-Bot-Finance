import os
import time
import logging
from typing import Dict, Any

from openai import OpenAI

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"


class LLMAPIError(Exception):
    pass

_client: OpenAI | None = None

def _get_client() -> OpenAI:
    """Singleton OpenAI client"""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMAPIError("OPENAI_API_KEY tidak ditemukan di environment")
        _client = OpenAI(api_key=api_key)
        logger.info("OpenAI client initialized")
    return _client


def call_llm(
    prompt: str,
    model_name: str = DEFAULT_MODEL,
    max_retries: int = 3,
    backoff_base: float = 0.8
) -> Dict[str, Any]:
    """
    Memanggil OpenAI API dan mengembalikan dict dengan text string valid.
    
    Args:
        prompt: User prompt untuk LLM
        model_name: Model OpenAI (default: gpt-4o-mini)
        max_retries: Jumlah retry jika gagal
        backoff_base: Base delay untuk exponential backoff
    
    Returns:
        Dict dengan keys:
            - text: Response text dari LLM (JSON string)
            - model: Model name yang digunakan
            - usage: Token usage metadata (dict)
    
    Raises:
        LLMAPIError: Jika API call gagal setelah retry
    """
    if not isinstance(prompt, str) or not prompt.strip():
        raise LLMAPIError("Prompt harus berupa string non-kosong")

    last_err = None
    client = _get_client()

    # System prompt untuk force JSON output
    messages = [
        {
            "role": "system",
            "content": (
                "You are a transaction parser for a finance application.\n"
                "Output MUST be a single valid JSON object.\n"
                "Do NOT include explanations, markdown, or extra text.\n\n"
                "JSON schema:\n"
                "{\n"
                '  "intent": "income | expense",\n'
                '  "amount": number,\n'
                '  "currency": "IDR",\n'
                '  "date": string | null,\n'
                '  "category": string,\n'
                '  "note": string,\n'
                '  "confidence": number\n'
                "}"
            )
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    for attempt in range(max_retries):
        try:
            logger.debug(f"Calling OpenAI API (attempt {attempt + 1}/{max_retries})")
            
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0,
                max_completion_tokens=512,
                response_format={"type": "json_object"}  # Force JSON output
            )

            text = response.choices[0].message.content

            if not isinstance(text, str) or not text.strip():
                raise LLMAPIError("LLM mengembalikan teks kosong atau invalid")

            logger.debug(f"RAW LLM OUTPUT:\n{text}")

            # Convert usage object to dict
            usage_dict = None
            if response.usage:
                usage_dict = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
                logger.info(f"Token usage: {usage_dict}")

            return {
                "text": text,
                "model": model_name,
                "usage": usage_dict
            }

        except Exception as e:
            last_err = e
            logger.warning(
                f"LLM error (attempt {attempt + 1}/{max_retries}): {e}",
                exc_info=True
            )
            if attempt < max_retries - 1:
                sleep_time = backoff_base * (2 ** attempt)
                logger.info(f"Retrying in {sleep_time}s...")
                time.sleep(sleep_time)

    raise LLMAPIError(
        f"Gagal memanggil LLM setelah {max_retries} percobaan"
    ) from last_err