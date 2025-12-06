import os
import time
from typing import Dict, Tuple, Optional
import logging

from ..ocr.preprocessor import ImagePreprocessor
from ..ocr.tesseract import TesseractOCR
from ..utils.image_utils import load_image, save_image, get_image_info

logger = logging.getLogger(__name__)

class OCRService:
    """
    OCR Service
    
    Orchestrates the complete OCR pipeline:
    - Image loading
    - Preprocessing
    - Text extraction
    - Metadata generation
    """
    
    def __init__(
        self,
        tesseract_cmd: Optional[str] = None,
        save_preprocessed: bool = False,
        preprocessed_dir: str = "upload/temp"
    ):
        """
        Initialize OCR Service
        
        Args:
            tesseract_cmd: Path ke Tesseract binary (optional)
            save_preprocessed: Save preprocessed images untuk debugging
            preprocessed_dir: Directory untuk save preprocessed images
        """
        # Initialize preprocessor
        self.preprocessor = ImagePreprocessor(
            max_width=1920,
            max_height=1080,
            auto_deskew=True,
            denoise=True
        )
        
        # Initialize Tesseract OCR
        self.ocr_engine = TesseractOCR(
            lang="ind+eng",
            psm=6,  # Uniform block of text
            oem=3,  # LSTM + Legacy
            tesseract_cmd=tesseract_cmd
        )
        
        self.save_preprocessed = save_preprocessed
        self.preprocessed_dir = preprocessed_dir
        
        # Create directory jika belum ada
        if self.save_preprocessed:
            os.makedirs(self.preprocessed_dir, exist_ok=True)
        
        logger.info("OCRService initialized")
    
    def process_image(self, image_path: str) -> Tuple[str, Dict]:
        """
        Process image dan extract text
        
        Args:
            image_path: Path ke image file
            
        Returns:
            Tuple[str, Dict]:
                - str: Extracted text
                - Dict: Metadata lengkap (OCR + preprocessing info)
                
        Raises:
            FileNotFoundError: Jika image tidak ditemukan
            RuntimeError: Jika OCR failed
        """
        logger.info(f"Processing image: {image_path}")
        start_time = time.time()
        
        try:
            # Step 1: Load image
            img = load_image(image_path)
            img_info = get_image_info(img)
            logger.info(f"Image loaded: {img_info['width']}x{img_info['height']}, "
                       f"{img_info['channels']} channels, {img_info['size_kb']:.2f} KB")
            
            # Step 2: Preprocess
            logger.info("Starting preprocessing...")
            preprocessed = self.preprocessor.preprocess(img)
            
            # Save preprocessed image untuk debugging (optional)
            if self.save_preprocessed:
                self._save_preprocessed_image(image_path, preprocessed)
            
            # Step 3: Extract text dengan OCR
            logger.info("Starting OCR extraction...")
            text, ocr_metadata = self.ocr_engine.extract_text(preprocessed)
            
            # Step 4: Build complete metadata
            processing_time = time.time() - start_time
            
            metadata = {
                # OCR metadata
                **ocr_metadata,
                
                # Image metadata
                "original_width": img_info['width'],
                "original_height": img_info['height'],
                "original_size_kb": img_info['size_kb'],
                
                # Processing metadata
                "processing_time_ms": int(processing_time * 1000),
                "preprocessed": True,
                "preprocessing_steps": [
                    "resize",
                    "grayscale",
                    "deskew" if self.preprocessor.auto_deskew else None,
                    "denoise" if self.preprocessor.denoise else None,
                    "binarize",
                    "morphology"
                ]
            }
            
            # Remove None values dari preprocessing_steps
            metadata["preprocessing_steps"] = [
                step for step in metadata["preprocessing_steps"] if step
            ]
            
            logger.info(f"OCR complete: {len(text)} chars extracted, "
                       f"confidence={ocr_metadata['confidence']:.2f}%, "
                       f"time={processing_time:.2f}s")
            
            return text, metadata
            
        except FileNotFoundError as e:
            logger.error(f"Image file not found: {image_path}")
            raise
        
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            raise RuntimeError(f"OCR processing failed: {e}")
    
    def _save_preprocessed_image(self, original_path: str, preprocessed_img) -> None:
        """
        Save preprocessed image untuk debugging
        
        Args:
            original_path: Path original image
            preprocessed_img: Preprocessed image array
        """
        try:
            # Generate filename
            filename = os.path.basename(original_path)
            name, ext = os.path.splitext(filename)
            preprocessed_filename = f"{name}_preprocessed{ext}"
            preprocessed_path = os.path.join(self.preprocessed_dir, preprocessed_filename)
            
            # Save image
            save_image(preprocessed_img, preprocessed_path)
            logger.debug(f"Saved preprocessed image: {preprocessed_path}")
            
        except Exception as e:
            logger.warning(f"Failed to save preprocessed image: {e}")
    
    def process_batch(self, image_paths: list) -> list:
        """
        Process multiple images in batch
        
        Args:
            image_paths: List of image paths
            
        Returns:
            List of tuples (text, metadata) untuk setiap image
        """
        logger.info(f"Processing batch of {len(image_paths)} images")
        
        results = []
        
        for i, path in enumerate(image_paths, 1):
            logger.info(f"Processing image {i}/{len(image_paths)}: {path}")
            
            try:
                text, metadata = self.process_image(path)
                results.append({
                    "path": path,
                    "success": True,
                    "text": text,
                    "metadata": metadata
                })
            except Exception as e:
                logger.error(f"Failed to process {path}: {e}")
                results.append({
                    "path": path,
                    "success": False,
                    "error": str(e)
                })
        
        success_count = sum(1 for r in results if r["success"])
        logger.info(f"Batch processing complete: {success_count}/{len(image_paths)} successful")
        
        return results