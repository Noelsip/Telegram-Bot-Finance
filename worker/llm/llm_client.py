import os
import time
import logging
from typing import Any, Dict

from groq import Groq

# Constants
DEFAULT_MODEL = "llama-3.1-8b-instant"
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 0.8

logger = logging.getLogger(__name__)

# Custom Exceptions
class LLMConfigurationError(Exception):
    """Kesalahan konfigurasi LLM (API key tidak ada, dsb)."""
    pass


class LLMAPIError(Exception):
    """Kesalahan saat memanggil API LLM."""
    pass


# Internal Helpers
def _ensure_configured() -> Groq:
    """
    Memastikan Groq API key tersedia dan client bisa dibuat.

    Returns:
        Instance Groq client.

    Raises:
        LLMConfigurationError: Jika API key tidak ditemukan.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise LLMConfigurationError(
            "GROQ_API_KEY tidak ditemukan di environment variables."
        )

    logger.debug("Groq API key terdeteksi.")
    return Groq(api_key=api_key)


def _extract_usage_metadata(usage: Any) -> Dict[str, int]:
    """
    Normalisasi metadata token usage dari Groq.

    Groq tidak selalu mengisi semua field, jadi kita aman-kan.
    """
    if not usage:
        return {
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
        }

    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }


# Public API (dipakai worker)
def call_llm(
    prompt: str,
    model_name: str = DEFAULT_MODEL,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_base: float = DEFAULT_BACKOFF_BASE
) -> Dict[str, Any]:
    """
    Memanggil LLM (Gemma-3-12B via Groq) untuk menghasilkan konten.

    Kontrak response dijaga agar kompatibel dengan worker lama.

    Args:
        prompt: Prompt teks untuk LLM.
        model_name: Nama model (default: gemma-3-12b).
        max_retries: Jumlah maksimal retry.
        backoff_base: Basis exponential backoff (detik).

    Returns:
        Dict standar:
        {
            "text": str,
            "model": str,
            "finish_reason": str,
            "usage": dict
        }
    """
    client = _ensure_configured()
    last_err = None

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a finance transaction parser. "
                            "Extract intent, amount, category, date clearly."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0
            )

            message = response.choices[0].message
            text = message.content or ""

            usage = getattr(response, "usage", None)

            return {
                "text": text,
                "model": model_name,
                "finish_reason": "stop",
                "usage": _extract_usage_metadata(usage),
            }

        except Exception as e:
            last_err = e
            logger.warning(
                "LLM error (attempt %s/%s): %s",
                attempt + 1,
                max_retries,
                str(e)
            )

            if attempt < max_retries - 1:
                time.sleep(backoff_base * (2 ** attempt))
            else:
                raise LLMAPIError("Gagal memanggil LLM") from last_err
