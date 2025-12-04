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
        tesseract_cmd: Optional[str] = None
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
        """
        Extract text dari image
        
        Args:
            img: Input image (grayscale atau RGB)
            
        Returns:
            Tuple[str, Dict]:
                - str: Extracted text
                - Dict: Metadata (confidence, word_count, etc)
        """
        logger.info("Starting OCR extraction...")

        # Build Tesseract config
        config = self._build_config()

        # Run OCR
        try:
            # Ekstrak text
            text = pytesseract.image_to_string(img, lang=self.lang, config=config)
            
            # Ekstrak data detail
            data = pytesseract.image_to_data(img, lang=self.lang, config=config, output_type=pytesseract.Output.DICT)
            
            # calkulasi metadata
            metadata = self._calculate_metadata(text, data)

            logger.info("OCR extraction completed.")
            return text, metadata
        except Exception as e:
            logger.error("Error during OCR extraction.")
            raise RuntimeError("Error during OCR extraction.") from e
        
    def _build_config(self) -> str:
        """
        Build Tesseract configuration string
        
        Returns:
            Config string untuk pytesseract
        """
        config_parts = []
        
        # PSM (Page Segmentation Mode)
        config_parts.append(f"--psm {self.psm}")
        
        # OEM (OCR Engine Mode)
        config_parts.append(f"--oem {self.oem}")
        
        # Additional optimizations untuk struk
        # - Preserve interword spaces
        # - Allow digits dan symbols
        config_parts.extend([
            "-c preserve_interword_spaces=1",
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
        # Filter out empty confidences (-1)
        confidences = [float(conf) for conf in data['conf'] if int(conf) != -1]
        
        # Calculate average confidence
        avg_confidence = np.mean(confidences) if confidences else 0.0
        
        # Count words (non-empty text entries)
        word_count = sum(1 for txt in data['text'] if txt.strip())
        
        # Count lines
        line_count = len(text.split('\n'))
        
        metadata = {
            "confidence": avg_confidence,
            "word_count": word_count,
            "char_count": len(text),
            "line_count": line_count,
            "tesseract_version": str(pytesseract.get_tesseract_version()),
            "language": self.lang,
            "psm": self.psm,
            "oem": self.oem
        }
        
        return metadata