import os
import time
from typing import Any, Dict, Optional, List
import google.generativeai as genai

DEFAULT_MODEL = "gemini-1.5-flash"

def _ensure_configured():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY tidak ditemukan di env")
    genai.configure(api_key=api_key)

def _build_model(model_name: str, generation_config:Optional[dict], safety_settings: Optional[list]):
    kwargs = {}
    if generation_config:
        kwargs["generation_config"] = generation_config
    if safety_settings:
        kwargs["safety_settings"] = safety_settings
    return genai.GenerativeModel(model_name=model_name, **kwargs)

def call_gemini (
    prompt: str,
    model_name: str = DEFAULT_MODEL,
    generation_config: Optional[dict] = None,
    safety_settings: Optional[list] = None,
    max_retries: int = 3,
    backoff_base: float = 0.8
) -> Dict[str, Any]:
    _ensure_configured()
    last_err = None
    for attempt in range(max_retries):
        try:
            model = _build_model(model_name, generation_config, safety_settings)
            response = model.generate_content(prompt)
            text = getattr(response, "text", "") or ""
            usage = getattr(response, "usage_metadata", {}) or {} 
            # mengambil finish reason jika tersedia
            finish_reason = "UNKNOWN"
            try:
                cand = (getattr(response, "candidates", []))
                fr = getattr(cand[0], "finish_reason", None)
                finish_reason = getattr(fr, "name", fr) or "UNKNOWN"
            except Exception as e:
                pass
            
            return {
                "text": text,
                "model": model_name,
                "finish_reason": finish_reason,
                "usage": {
                    "prompt_tokens": getattr(usage, "prompt_token_count", 0) or usage.get("prompt_token_count", 0),
                    "completion_tokens": getattr(usage, "candidates_token_count", 0) or usage.get("candidates_token_count", 0),
                    "total_tokens": getattr(usage, "total_token_count", 0) or usage.get("total_token_count", 0),
                },
            }
        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(backoff_base * (2 ** attempt))
            else:
                raise last_err