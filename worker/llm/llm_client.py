import os
import time
import logging
from typing import Dict, Any

from groq import Groq

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama-3.1-8b-instant"


class LLMAPIError(Exception):
    pass


_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise LLMAPIError("GROQ_API_KEY tidak ditemukan di environment")
        _client = Groq(api_key=api_key)
    return _client


def call_llm(
    prompt: str,
    model_name: str = DEFAULT_MODEL,
    max_retries: int = 3,
    backoff_base: float = 0.8
) -> Dict[str, Any]:
    """
    Memanggil LLM dan SELALU mengembalikan dict dengan text string valid.
    """
    if not isinstance(prompt, str) or not prompt.strip():
        raise LLMAPIError("Prompt harus berupa string non-kosong")

    last_err = None
    client = _get_client()

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
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0
            )

            text = response.choices[0].message.content

            if not isinstance(text, str) or not text.strip():
                raise LLMAPIError("LLM mengembalikan teks kosong atau invalid")

            logger.debug("RAW LLM OUTPUT:\n%s", text)

            return {
                "text": text,
                "model": model_name,
                "usage": getattr(response, "usage", None)
            }

        except Exception as e:
            last_err = e
            logger.warning(
                "LLM error (attempt %s/%s): %s",
                attempt + 1, max_retries, e
            )
            time.sleep(backoff_base * (2 ** attempt))

    raise LLMAPIError("Gagal memanggil LLM") from last_err
