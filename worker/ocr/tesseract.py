import pytesseract
import cv2
import numpy as np
from typing import Dict, Optional, Tuple, List
import logging
import os

logger = logging.getLogger(__name__)

class TesseractOCR:
    """
    Enhanced Tesseract OCR Engine
    
    Features:
    - Multiple PSM attempts
    - Confidence-based selection
    - Whitelist optimization for receipts
    """
    
    def __init__(
        self,
        lang: str = "ind+eng",
        tesseract_cmd: Optional[str] = None
    ):
        self.lang = lang
        
        # ✅ PSM modes to try (in order of priority for receipts)
        self.psm_modes = [
            6,   # Uniform block of text (best for receipts)
            4,   # Single column of text
            3,   # Fully automatic
            11,  # Sparse text
            12   # Sparse text with OSD
        ]
        
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            logger.info(f"Set tesseract command to: {tesseract_cmd}")
        
        self._verify_installation()
        logger.info(f"TesseractOCR initialized: lang={lang}")
    
    def _verify_installation(self):
        """Verify Tesseract installation"""
        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract version: {version}")
        except Exception as e:
            logger.error("Tesseract not found")
            raise RuntimeError("Tesseract not installed") from e
    
    def extract_text(self, img: np.ndarray) -> Tuple[str, Dict]:
        """
        Extract text with multiple PSM attempts
        Choose best result based on confidence
        """
        attempts = []
        
        for psm in self.psm_modes:
            try:
                logger.debug(f"Trying PSM {psm}...")
                
                config = self._build_config(psm)
                
                # Extract text
                text = pytesseract.image_to_string(
                    img,
                    lang=self.lang,
                    config=config
                ).strip()
                
                # Get detailed data
                data = pytesseract.image_to_data(
                    img,
                    lang=self.lang,
                    config=config,
                    output_type=pytesseract.Output.DICT
                )
                
                metadata = self._calculate_metadata(text, data)
                metadata['psm_used'] = psm
                
                attempts.append({
                    'psm': psm,
                    'text': text,
                    'metadata': metadata,
                    'score': self._calculate_score(text, metadata)
                })
                
                logger.debug(
                    f"PSM {psm}: {len(text)} chars, "
                    f"confidence={metadata['confidence']:.1f}%, "
                    f"score={attempts[-1]['score']:.2f}"
                )
                
                # Early exit if excellent result
                if metadata['confidence'] > 85 and len(text) > 50:
                    logger.info(f"Excellent result with PSM {psm}, stopping early")
                    break
                
            except Exception as e:
                logger.warning(f"PSM {psm} failed: {e}")
                continue
        
        if not attempts:
            logger.error("All OCR attempts failed")
            return "", {"confidence": 0.0, "error": "All attempts failed"}
        
        # Choose best attempt
        best = max(attempts, key=lambda x: x['score'])
        best['metadata']['attempts'] = [
            {'psm': a['psm'], 'confidence': a['metadata']['confidence']}
            for a in attempts
        ]
        
        logger.info(
            f"✅ Best result: PSM {best['psm']}, "
            f"{len(best['text'])} chars, "
            f"confidence={best['metadata']['confidence']:.1f}%"
        )
        
        return best['text'], best['metadata']
    
    def _build_config(self, psm: int) -> str:
        """
        Build Tesseract config - optimized for receipts
        """
        config_parts = [
            f"--psm {psm}",
            "--oem 3",  # LSTM + Legacy
            "--dpi 300",
            "-c preserve_interword_spaces=1",
        ]
        
        # ✅ Receipt-optimized whitelist
        # Allow: letters, numbers, common punctuation, Indonesian/English chars
        whitelist = (
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "abcdefghijklmnopqrstuvwxyz"
            "0123456789"
            ".,;:!?'-/()[]{}@#$%&*+=<> \n\t"
            "RpIDR"  # Currency symbols
        )
        
        config_parts.append(f"-c tessedit_char_whitelist={whitelist}")
        
        return " ".join(config_parts)
    
    def _calculate_metadata(self, text: str, data: Dict) -> Dict:
        """Calculate OCR metadata"""
        non_empty_words = [txt for txt in data["text"] if txt.strip()]
        word_count = len(non_empty_words)
        
        if word_count == 0 or not text.strip():
            return {
                "confidence": 0.0,
                "word_count": 0,
                "char_count": 0,
                "line_count": 0
            }
        
        # Calculate average confidence (only for valid words)
        confidences = [
            float(conf)
            for conf, txt in zip(data["conf"], data["text"])
            if int(conf) != -1 and txt.strip()
        ]
        
        avg_confidence = np.mean(confidences) if confidences else 0.0
        
        # Count lines
        line_count = len([ln for ln in text.split("\n") if ln.strip()]) or 1
        
        return {
            "confidence": float(avg_confidence),
            "word_count": word_count,
            "char_count": len(text),
            "line_count": line_count,
            "tesseract_version": str(pytesseract.get_tesseract_version()),
            "language": self.lang
        }
    
    def _calculate_score(self, text: str, metadata: Dict) -> float:
        """
        Calculate quality score untuk memilih best OCR result
        
        Factors:
        - Confidence (weight: 0.5)
        - Text length (weight: 0.3)
        - Word count (weight: 0.2)
        """
        confidence_score = metadata['confidence'] / 100.0
        
        # Normalize text length (ideal: 100-1000 chars)
        char_count = metadata['char_count']
        if char_count < 50:
            length_score = char_count / 50.0
        elif char_count > 1000:
            length_score = 1000.0 / char_count
        else:
            length_score = 1.0
        
        # Normalize word count (ideal: 20-200 words)
        word_count = metadata['word_count']
        if word_count < 10:
            word_score = word_count / 10.0
        elif word_count > 200:
            word_score = 200.0 / word_count
        else:
            word_score = 1.0
        
        # Weighted score
        total_score = (
            confidence_score * 0.5 +
            length_score * 0.3 +
            word_score * 0.2
        )
        
        return total_score