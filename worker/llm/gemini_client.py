import os
import time
import logging
from typing import Any, Dict, Optional

import google.generativeai as genai

# Constants
DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 0.8

logger = logging.getLogger(__name__)

class GeminiConfigurationError(Exception):
    """Custom exception untuk kesalahan konfigurasi Gemini."""
    pass

class GeminiAPIError(Exception):
    """Custom exception untuk kesalahan saat memanggil API Gemini."""
    pass

def _ensure_configured() -> None:
    """
    Memvalidasi dan mengkonfigurasi API Gemini dengan api key dari env.
    
    Raises:
        GeminiConfigurationError: Jika API key tidak ditemukan.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiConfigurationError(
            "Gemini API tidak ditemukan di env variables."
            " Silakan set gemini api key terlebih dahulu."
        )
    genai.configure(api_key=api_key)
    logger.debug("Gemini API berhasil dikonfigurasi.")

def _build_model(
    model_name: str,
    generation_config:Optional[dict],
    safety_settings: Optional[list]
) -> genai.GenerativeModel:
    """ 
        Membuat instance model Gemini dengan konfigurasi yang diberikan.

    Args:
        model_name (str): Nama model Gemini.
        generation_config (Optional[dict]): Konfigurasi untuk generation konten
        safety_settings (Optional[list]): Pengaturan keamanan untuk model.
        
    Returns:
        Instance GenerativeModel yang telah dikonfigurasi.
    """
    kwargs = {}
    
    if generation_config:
        kwargs["generation_config"] = generation_config

    if safety_settings:
        kwargs["safety_settings"] = safety_settings

    return genai.GenerativeModel(model_name=model_name, **kwargs)

def _extract_finish_reason(response: Any) -> str:
    """
    Mengekstrak finish reason dari response Gemini API.
    
    Args:
        response: Response object dari Gemini API.
    
    Returns:
        String finish reason atau "UNKNOWN" jika tidak ditemukan.
    """
    try:
        candidates = getattr(response, "candidates", [])
        if candidates:
            finish_reason = getattr(candidates[0], "finish_reason", None)
            return getattr(finish_reason, "name", finish_reason) or "UNKNOWN"
    except Exception:
        pass
    
    return "UNKNOWN"

def _extract_usage_metadata(usage: Any) -> Dict[str, int]:
    """
    Mengekstrak metadata penggunaan token dari respon

    Args:
        usage (Any): Usage metadata dari respon Gemini.

    Returns:
        Dictionary berisi informasi prompt_tokens, completion_tokens, dan total_tokens.
    """
    # support baik attribut maupun dict access
    prompt_tokens = getattr(usage, "prompt_token_count", 0) or usage.get("prompt_token_count", 0)
    completion_tokens = getattr(usage, "candidates_token_count", 0) or usage.get("candidates_token_count", 0)
    total_tokens = getattr(usage, "total_token_count", 0) or usage.get("total_token_count", 0)
    
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }

def call_gemini (
    prompt: str,
    model_name: str = DEFAULT_MODEL,
    generation_config: Optional[dict] = None,
    safety_settings: Optional[list] = None,
    max_retries: int = 3,
    backoff_base: float = 0.8
) -> Dict[str, Any]:
    """
    Memanggil Gemini API untuk menghasilkan konten berdasarkan prompt.
    
    Fungsi ini akan melakukan retry dengan exponential backoff jika terjadi error.
    
    Args:
        prompt: Teks prompt untuk dikirim ke model.
        model_name: Nama model Gemini yang akan digunakan.
        generation_config: Konfigurasi untuk generasi konten (opsional).
        safety_settings: Pengaturan keamanan konten (opsional).
        max_retries: Jumlah maksimal percobaan ulang jika terjadi error.
        backoff_base: Basis waktu untuk exponential backoff (dalam detik).
    
    Returns:
        Dictionary berisi:
            - text: Teks hasil generasi dari model
            - model: Nama model yang digunakan
            - finish_reason: Alasan selesainya generasi
            - usage: Informasi penggunaan token
    
    Raises:
        GeminiConfigurationError: Jika konfigurasi API gagal.
        Exception: Error terakhir yang terjadi setelah max_retries tercapai.
    """
    _ensure_configured()
    
    last_err = None
    
    for attempt in range(max_retries):
        try:
            # Membuat model dengan konfigurasi yang diberikan
            model = _build_model(model_name, generation_config, safety_settings)

            # Mengirim request ke Gemini API
            response = model.generate_content(prompt)

            # Mengekstrak text hasil generate
            text = getattr(response, "text", "") or ""

            # Mengekstrak usage metadata
            usage = getattr(response, "usage_metadata", {}) or {}

            # Menyusun response dalam format standar
            return {
                "text": text,
                "model": model_name,
                "finish_reason": _extract_finish_reason(response),
                "usage": _extract_usage_metadata(usage),
            }
        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(backoff_base * (2 ** attempt))
            else:
                raise last_err