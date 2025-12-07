import pytesseract
import cv2
import numpy as np
from typing import Dict, Optional, Tuple
import logging
import os

logger = logging.getLogger(__name__)

class TesseractOCR:
    """
    Tesseract OCR Engine
    
    Features:
    - Multi-language support (Indonesian + English)
    - PSM (Page Segmentation Mode) optimization
    - OEM (OCR Engine Mode) selection
    - Confidence scoring
    """
    
    def __init__(
        self,
        lang: str = "ind+eng",
        psm: int = 6,
        oem: int = 3,
        tesseract_cmd: Optional[str] = None,
        fallback_psm_modes: Optional[list[int]] = None,
        min_break_confidence: float = 65.0
    ):
        """
        Initialize Tesseract OCR
        
        Args:
            lang: Language(s) untuk OCR. Format: "ind+eng"
                  - ind: Indonesian
                  - eng: English
            psm: Page Segmentation Mode
                 - 6: Uniform block of text (default, best untuk struk)
                 - 3: Fully automatic
                 - 11: Sparse text (untuk text acak)
            oem: OCR Engine Mode
                 - 3: Default (LSTM + Legacy) - RECOMMENDED
                 - 1: LSTM only (faster, modern)
                 - 0: Legacy only (slower, sometimes more accurate)
            tesseract_cmd: Path ke tesseract binary (optional)
        """
        self.lang = lang
        self.psm = psm
        self.oem = oem
        # Fokus ke mode blok teks/sedikit otomatis: 6 (block), 3 (auto), 4 (single column)
        self.fallback_psm_modes = fallback_psm_modes or [psm, 3, 4]
        self.min_break_confidence = min_break_confidence
        
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            logger.info(f"Set tesseract command to: {tesseract_cmd}")
            
        # Verify Tesseract installed
        self._verify_installation()
        
        logger.info(f"TesseractOCR initialized: lang={lang}, psm={psm}, oem={oem}")

    def _verify_installation(self):
        """
        Verify Tesseract terinstall dan accessible
        
        Raises:
            RuntimeError: Jika Tesseract tidak ditemukan
        """
        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract version: {version}")
        except Exception as e:
            logger.error("Tesseract tidak ditemukan atau tidak terinstall dengan benar.")
            raise RuntimeError("Tesseract tidak ditemukan atau tidak terinstall dengan benar.") from e
        
    def extract_text(self, img: np.ndarray) -> Tuple[str, Dict]:
        """Extract text dari image dengan beberapa percobaan PSM.

        Menggunakan beberapa nilai PSM secara berurutan dan memilih hasil
        dengan confidence terbaik. Berhenti lebih awal jika sudah melewati
        ambang `min_break_confidence`.
        """
        attempts = []
        best_text = ""
        best_metadata: Dict = {"confidence": 0.0}

        for attempt_psm in self.fallback_psm_modes:
            config = self._build_config(psm_override=attempt_psm)

            # Jalankan OCR
            text = pytesseract.image_to_string(
                img,
                lang=self.lang,
                config=config,
            )
            data = pytesseract.image_to_data(
                img,
                lang=self.lang,
                config=config,
                output_type=pytesseract.Output.DICT,
            )

            metadata = self._calculate_metadata(text, data)
            metadata["psm_used"] = attempt_psm
            attempts.append({
                "psm": attempt_psm,
                "confidence": metadata["confidence"],
            })

            if metadata["confidence"] > best_metadata.get("confidence", 0.0):
                best_text = text.strip()
                best_metadata = metadata

            if metadata["confidence"] >= self.min_break_confidence:
                break

        best_metadata["attempts"] = attempts
        return best_text, best_metadata
           
    def _build_config(self, psm_override: Optional[int] = None) -> str:
        """
        Build Tesseract configuration string
        
        Returns:
            Config string untuk pytesseract
        """
        config_parts = []
        
        # PSM (Page Segmentation Mode)
        psm_value = psm_override if psm_override is not None else self.psm
        config_parts.append(f"--psm {psm_value}")
        
        # OEM (OCR Engine Mode)
        config_parts.append(f"--oem {self.oem}")

        # Hint DPI agar Tesseract menganggap gambar cukup tajam
        config_parts.append("--dpi 300")
        
        # Additional optimizations untuk struk
        # - Preserve interword spaces
        # - Batasi karakter ke huruf, angka, dan tanda baca umum
        config_parts.extend([
            "-c preserve_interword_spaces=1",
            "-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789./:-, ",
        ])
        
        return " ".join(config_parts)

    def _calculate_metadata(self, text: str, data: Dict) -> Dict:
        """
        Calculate OCR metadata dari hasil
        
        Args:
            text: Extracted text
            data: Detailed OCR data dari image_to_data
            
        Returns:
            Dict dengan metadata:
                - confidence: Average confidence (0-100)
                - word_count: Jumlah words terdeteksi
                - char_count: Jumlah characters
                - line_count: Jumlah lines
        """
        # Hitung kata non-kosong dari data image_to_data
        non_empty_words = [txt for txt in data["text"] if txt.strip()]
        word_count = len(non_empty_words)

        # Jika tidak ada kata sama sekali atau text kosong, anggap confidence 0
        if word_count == 0 or not text.strip():
            avg_confidence = 0.0
        else:
            # Filter out empty confidences (-1) dan hanya untuk teks non-kosong
            confidences = [
                float(conf)
                for conf, txt in zip(data["conf"], data["text"])
                if int(conf) != -1 and txt.strip()
            ]
            avg_confidence = np.mean(confidences) if confidences else 0.0

        # Count lines (hanya baris yang tidak kosong)
        line_count = len([ln for ln in text.split("\n") if ln.strip()]) or 1

        metadata = {
            "confidence": avg_confidence,
            "word_count": word_count,
            "char_count": len(text),
            "line_count": line_count,
            "tesseract_version": str(pytesseract.get_tesseract_version()),
            "language": self.lang,
            "psm": self.psm,
            "oem": self.oem,
        }

        return metadata