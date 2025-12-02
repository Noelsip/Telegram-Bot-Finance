"""
================================================================================
FILE: worker/llm/gemini_client.py
DESKRIPSI: Google Gemini API Client
ASSIGNEE: @Backend/ML
PRIORITY: HIGH
SPRINT: 2
================================================================================

DEPENDENCIES:
- google-generativeai

INSTALL:
pip install google-generativeai

ENVIRONMENT VARIABLE:
- GEMINI_API_KEY: API key dari Google AI Studio (https://aistudio.google.com/)

TODO [LLM-001]: Initialize Gemini Client
- Import google.generativeai as genai
- Configure dengan API key: genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
- Buat model instance: genai.GenerativeModel("gemini-1.5-flash")

MODEL OPTIONS:
- gemini-1.5-flash: Cepat, murah, cukup untuk parsing (RECOMMENDED)
- gemini-1.5-pro: Lebih akurat tapi lebih mahal
- gemini-1.0-pro: Legacy, masih bisa dipakai

TODO [LLM-002]: call_gemini(prompt, model_name="gemini-1.5-flash") -> dict
Fungsi untuk memanggil Gemini API.

Parameter:
- prompt: str - Full prompt termasuk system instruction dan few-shot examples
- model_name: str - Nama model yang digunakan

Return:
{
    "text": str,           # Raw response text dari LLM
    "model": str,          # Model yang digunakan
    "finish_reason": str,  # "STOP", "MAX_TOKENS", etc.
    "usage": {
        "prompt_tokens": int,
        "completion_tokens": int,
        "total_tokens": int
    }
}

Langkah:
1. Buat model instance dengan model_name
2. Call generate_content(prompt)
3. Extract text dari response.text
4. Extract usage dari response.usage_metadata
5. Return formatted dict

TODO [LLM-003]: Error Handling
Handle errors yang mungkin terjadi:
- google.api_core.exceptions.ResourceExhausted: Rate limit exceeded
- google.api_core.exceptions.InvalidArgument: Invalid prompt
- google.api_core.exceptions.PermissionDenied: Invalid API key
- Network errors

Untuk rate limit, implement exponential backoff retry.

TODO [LLM-004]: Generation Config (Opsional)
Customize generation parameters:

generation_config = {
    "temperature": 0.1,      # Low untuk consistent output
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 1024,
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config
)

TODO [LLM-005]: Safety Settings (Opsional)
Disable safety filters jika perlu (untuk financial data):

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    ...
]

CATATAN:
- Gemini API gratis dengan rate limit (15 RPM untuk flash)
- Untuk production, pertimbangkan paid tier
- Response time biasanya 1-3 detik
================================================================================
"""
