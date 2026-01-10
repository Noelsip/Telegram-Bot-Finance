import logging
import json
from typing import Dict, Optional, Literal
from enum import Enum

from worker.llm.llm_client import call_llm, LLMAPIError

logger = logging.getLogger(__name__)

class UserIntent(str, Enum):
    """
        User intent types
    """
    TRANSACTION = "transaction"
    HELP = "help"
    HISTORY = "history"
    EXPORT = "export"
    SMALL_TALK = "small_talk"
    UNKNOWN = "unknown"
    
class IntentClassifier:
    """
        LLM-powered intent classifier
        Mengklasifikasikan user message ke salah satu intent category
    """
    def __init__(self):
        self.model = "gpt-4o-mini"
        logger.info("IntentClassifier initialized with model %s", self.model)
        
    async def classify(self, text: str) -> Dict:
        """
            Classify user message intent
            
            Args:
                text (str): User message text
            
            Returns:
                Dict dengan keys:
                    - intent (UserIntent): Kategori intent yang terklasifikasi
                    - confidence (float): Confidence score dari klasifikasi
                    - period: Optional[str] untuk filter income/expense
                    - reasion: str (why LLM chose this intent)
        """
        try:
            logger.info("Classifying intent for text: ", text[:100] + "...")

            # membangub clasifikasi prompt
            prompt = self._build_classification_prompt(text)
            
            # Call LLM
            response = call_llm(
                prompt=prompt,
                model_name=self.model,
                max_retries=2
            )
            
            llm_text = response.get("text", "")

            # parse JSON response
            result = self._parse_llm_response(llm_text)
            
            logger.info(
                f"Intent classified: {result['intent']} "
                f"(confidence: {result['confidence']:.2f})"
            )
            
            return result
        except Exception as e:
            logger.error(f"Intent classification failed: {str(e)}", exc_info=True)

            # Fallback
            return {
                "intent": UserIntent.TRANSACTION,
                "confidence": 0.3,
                "period": None,
                "direction": None,
                "reason": "Fallback due to error"
            }
    def _build_classification_prompt(self, text: str) -> str:
        """
            Build the prompt for intent classification
        """
        system = """
            Kamu adalah AI classifier untuk aplikasi keuangan pribadi.
            
            Tugas: 
            Klasifikasikan user message ke salah satu kategorui intent berikut:
            1. transaction: User ingin mencatat transaksi income/expense.
                contoh: "Saya belanja di supermarket 50 ribu", "Saya menerima gaji 5 juta", "Catat pengeluaran 20 ribu untuk makan siang", "transfer 100 ribu"
            2. help: User meminta bantuan atau panduan penggunaan aplikasi.
                contoh: "Bagaimana cara menambahkan transaksi?", "Tolong bantu saya menggunakan aplikasi ini", "help"
            3. history: User ingin melihat riwayat transaksi.
                contoh: "lihat transaksi hari ini", "Tampilkan riwayat pengeluaran saya", "Apa saja transaksi saya minggu lalu?", "history minggu ini", "rekap bukan ini"
            4. export: User ingin mengekspor data transaksi.
                contoh: "Ekspor data transaksi saya", "Saya ingin mengunduh riwayat transaksi", "export transaksi bulan lalu", "download data keuangan", "kirim excel", "download laporan"
            5. small_talk: User melakukan percakapan ringan atau obrolan umum.
                contoh: "Hai, apa kabar?", "terimakasih", "Selamat pagi!", "Apa yang bisa kamu lakukan?"
            6. unknown: Jika intent user tidak jelas atau tidak sesuai dengan kategori di atas.
                contoh: "Saya suka es krim", "Cuaca hari ini cerah", "Apa itu AI?"
            PERIOD DETECTION (untuk history/export):
            - "hari ini", "today", "harian" → "today"
            - "minggu ini", "mingguan", "7 hari", "seminggu" → "week"
            - "bulan ini", "bulanan", "30 hari" → "month"
            - "tahun ini", "tahunan", "365 hari" → "year"

            DIRECTION DETECTION (untuk history/export filter):
            - "pemasukan", "income", "uang masuk" → "income"
            - "pengeluaran", "expense", "uang keluar" → "expense"

            Output JSON format:
            {
                "intent": "transaction|help|history|export|small_talk|unknown",
                "confidence": 0.0-1.0,
                "period": "today|week|month|year" (null jika tidak relevan),
                "direction": "income|expense" (null jika tidak relevan),
                "reasoning": "Brief explanation why you chose this intent"
            }

            IMPORTANT:
            - Prioritas utama: detect TRANSACTION vs NON-TRANSACTION
            - Jika ada nominal uang/angka → kemungkinan besar transaction
            - Jika ada kata "help", "bantuan", "cara" → help
            - Jika ada kata "history", "riwayat", "lihat" → history
            - Small talk biasanya sangat pendek (1-3 kata) tanpa context keuangan
            """
            
        user_input = f"""
            User message: "{text}"
            """
        
        return system + "\n" + user_input
    def _parse_llm_response(self, llm_text: str) -> Dict:
        """
            Parse the LLM response text into structured data
        """
        try:
            json_start = llm_text.find("{")
            json_end = llm_text.rfind("}") + 1
            
            if json_start == -1 or json_end == -1:
                raise ValueError("No JSON object found in LLM response")
            
            json_str = llm_text[json_start:json_end]
            data = json.loads(json_str)
            
            # validate and normalize data
            intent_str = data.get("intent", "unknown").lower()
            
            # map to enum
            try:
                intent = UserIntent(intent_str)
            except ValueError:
                logger.warning(f"Unknown intent from LLM: {intent_str}")
                intent = UserIntent.UNKNOWN
                
            return {
                "intent": intent,
                "confidence": float(data.get("confidence", 0.5)),
                "period": data.get("period"),
                "direction": data.get("direction"),
                "reason": data.get("reasoning", "")
            }
            
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {str(e)}")
            logger.debug(f"LLM response text: {llm_text}")
            
            # Fallback
            return {
                "intent": UserIntent.UNKNOWN,
                "confidence": 0.0,
                "period": None,
                "direction": None,
                "reason": "Failed to parse LLM response"
            }
# Singleton instance
_classifier: Optional[IntentClassifier] = None

async def classify_intent(text: str) -> Dict:
    """
        Main function untuk classify user intent
        
        Args:
            text (str): Raw user message text
            
        Returns:
            Dict dengan intent classification result
    """
    global _classifier
    
    if _classifier is None:
        _classifier = IntentClassifier()
    return await _classifier.classify(text)

# # Helper function untuk backward compatibility
# async def get_intent_and_params(text: str) -> tuple[str, Optional[str], Optional[str]]:
#     """
#         Wrapper function yang compatible dengan signature lama
        
#         Returns:
#             Tuple[intent, period, direction]
#     """
#     result = await clarify_intent(text)
    
#     intent_str = result["intent"].value
#     period = result.get("period")
#     direction = result.get("direction")
    
#     # Map to old format
#     if intent_str == "small_talk":
#         return None, None, None
#     elif intent_str == "unknown":
#         return "transaction", None, None
#     else:
#         return intent_str, period, direction