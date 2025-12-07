import logging
from typing import Optional, Dict, Any

from app.models import InputType, IntentType
from worker.llm.prompts import build_prompt
from worker.llm.gemini_client import call_gemini
from worker.llm.parser import parse_llm_response
from worker.services.ocr_service import OCRService

logger = logging.getLogger(__name__)

class ProcessMessageJob:
    """Job buat proses pesan masuk (text/image)"""
    def __init__(self, user_id: int, input_type: str, data: Dict[str, Any]):
        """
        Args:
            user_id: ID user (Telegram/WhatsApp)
            input_type: "text" atau "image"
            data: Data tambahan (text content, file_path, receipt_id, dll)
        """
        self.user_id = user_id
        
        #normalize input type ke enum
        try:
            self.input_type : InputType = (
                input_type if isinstance(input_type, InputType) 
                else InputType(input_type)
            )
        except ValueError:
            logger.error(f"Invalid input type: {input_type}")
            self.input_type = InputType.TEXT  # default ke text
            
        self.data = data
        self.ocr_service = OCRService()

    """Job buat ekseskusi pesan"""
    async def execute(self) -> Optional[Dict]:
        """Pilah berdasarkan tipe input"""
        try:
            if self.input_type is InputType.TEXT:
                return await self._process_text()
            elif self.input_type is InputType.IMAGE:
                return await self._process_image()
            else:
                logger.error(f"Unknown input type: {self.input_type}")
                return None
        except Exception as e:
            logger.error(f"Job execution failed: {e}", exc_info=True)
            return None

    """Job buat proses teks"""
    async def _process_text(self) -> Optional[Dict]:
        text = self.data.get("text", "")
        if not text:
            return None
        
        #build prompt dan panggil LLM
        llm_output = await self._build_and_call_llm(text)
        
        #klasifikasi hasil LLM
        parsed_output = parse_llm_response(llm_output)
        
        #Tentukan review flag
        needs_review = self._determine_review_flag(parsed_output)

        return {
            "user_id": self.user_id,
            "input_type": self.input_type.value,
            "input_text": text,
            "llm_output": llm_output,
            "parsed_output": parsed_output,
            "needs_review": needs_review
        }

    """Job buat proses gambar"""
    async def _process_image(self) -> Optional[Dict]:
        file_path = self.data.get("file_path")
        receipt_id = self.data.get("receipt_id")
        
        if not file_path:
            return None
        
        #Lakukan OCR pada gambar
        ocr_text, ocr_meta = self.ocr_service.process_image(file_path)
        
        #build prompt dan panggil LLM
        llm_output = await self._build_and_call_llm(ocr_text)
        
        #klasifikasi hasil LLM
        parsed_output = parse_llm_response(llm_output)
        
        #Tentukan review flag
        needs_review = self._determine_review_flag(parsed_output)
        
        return {
            "user_id": self.user_id,
            "input_type": self.input_type.value,
            "receipt_id": receipt_id,
            "ocr_text": ocr_text,
            "ocr_meta": ocr_meta,
            "llm_output": llm_output,
            "parsed_output": parsed_output,
            "needs_review": needs_review
        }

    """ngebuild prompt dan manggil LLM"""
    async def _build_and_call_llm(self, text: str) -> str:
        prompt = build_prompt(text)
        llm_response = await call_gemini(
            prompt,
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 512}
        )
        return llm_response
    
    """nentuin transaksi perlu review manual atau enggak"""
    def _determine_review_flag(self, parsed_output: Optional[Dict]) -> bool:
        if not parsed_output:
            return True
        
        #low confidense
        if parsed_output.get("confidence", 0) < 0.5:
            return True
        
        #parse gagal
        if not parsed_output.get("parse_success", False):
            return True
        
        #amount ga valid
        amount = parsed_output.get("amount", 0)
        if amount < 0:
            return True
        
        # cek intent
        raw_intent = parsed_output.get("intent")

        try:
            intent = IntentType(raw_intent)
        except Exception:
        # intent tidak dikenal
            return True

        # Dua intent valid → PEMASUKKAN atau PENGELUARAN
        if intent not in [IntentType.PEMASUKKAN, IntentType.PENGELUARAN]:
            return True
        
        return False