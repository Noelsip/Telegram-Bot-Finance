import cv2
import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class ImagePreprocessor:
    """
    Image preprocessor untuk OCR - OPTIMIZED untuk struk
    
    Pipeline adaptif:
    - Auto-detect quality
    - Dynamic preprocessing based on image condition
    - Multiple enhancement techniques
    """
    
    def __init__(
        self,
        target_height: int = 1600,  # ✅ INCREASED untuk detail lebih baik
        auto_deskew: bool = True,
        denoise: bool = True,
        aggressive_mode: bool = False  # ✅ NEW: Mode agresif untuk struk buruk
    ):
        self.target_height = target_height
        self.auto_deskew = auto_deskew
        self.denoise = denoise
        self.aggressive_mode = aggressive_mode
        
    def preprocess(self, img: np.ndarray) -> np.ndarray:
        """
        Adaptive preprocessing pipeline
        """
        logger.info(f"Starting adaptive preprocessing, input shape: {img.shape}")
        
        # 1. Detect image quality
        quality = self._assess_quality(img)
        logger.info(f"Image quality assessment: {quality}")
        
        # 2. Adaptive resize (upscale kecil, downscale besar)
        img = self._adaptive_resize(img)
        logger.info(f"After adaptive resize: {img.shape}")
        
        # 3. Convert to grayscale
        gray = self._to_grayscale(img)
        
        # 4. Conditional enhancement based on quality
        if quality['is_dark']:
            logger.info("Applying brightness enhancement")
            gray = self._enhance_brightness(gray)
        
        if quality['is_blurry']:
            logger.info("Applying sharpening")
            gray = self._sharpen(gray)
        
        if quality['low_contrast']:
            logger.info("Applying contrast enhancement (CLAHE)")
            gray = self._enhance_contrast(gray)
        
        # 5. Deskewing
        if self.auto_deskew:
            gray = self._deskew(gray)
            logger.info("After deskewing")
        
        # 6. Denoising
        if self.denoise:
            gray = self._denoise(gray, strength=10 if quality['is_noisy'] else 7)
            logger.info("After denoising")
        
        # 7. Adaptive binarization
        binary = self._adaptive_binarize(gray)
        logger.info("After adaptive binarization")
        
        # 8. Morphological cleaning (optional)
        if self.aggressive_mode or quality['needs_cleanup']:
            result = self._morphology(binary)
            logger.info("After morphological operations")
        else:
            result = binary
        
        logger.info("Preprocessing completed")
        return result
    
    def _assess_quality(self, img: np.ndarray) -> dict:
        """
        Assess image quality untuk menentukan preprocessing strategy
        """
        gray = self._to_grayscale(img) if len(img.shape) == 3 else img
        
        # Check brightness
        mean_brightness = np.mean(gray)
        is_dark = mean_brightness < 100
        is_bright = mean_brightness > 180
        
        # Check contrast
        contrast = gray.std()
        low_contrast = contrast < 40
        
        # Check blur (Laplacian variance)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        blur_score = laplacian.var()
        is_blurry = blur_score < 100
        
        # Check noise (high frequency content)
        noise_score = np.mean(np.abs(cv2.Sobel(gray, cv2.CV_64F, 1, 1)))
        is_noisy = noise_score > 50
        
        return {
            'is_dark': is_dark,
            'is_bright': is_bright,
            'low_contrast': low_contrast,
            'is_blurry': is_blurry,
            'is_noisy': is_noisy,
            'needs_cleanup': is_noisy or low_contrast,
            'mean_brightness': mean_brightness,
            'contrast': contrast,
            'blur_score': blur_score
        }
    
    def _adaptive_resize(self, img: np.ndarray) -> np.ndarray:
        """
        Adaptive resize - upscale kecil, downscale besar
        Target: consistent height untuk OCR optimal
        """
        h, w = img.shape[:2]
        
        # Calculate scale based on target height
        scale = self.target_height / h
        new_w = int(w * scale)
        new_h = self.target_height
        
        # Upscale (for small images) - use CUBIC interpolation
        if scale > 1.0:
            logger.info(f"Upscaling from {w}x{h} to {new_w}x{new_h}")
            return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        
        # Downscale (for large images) - use AREA interpolation
        elif scale < 1.0:
            logger.info(f"Downscaling from {w}x{h} to {new_w}x{new_h}")
            return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        return img
    
    def _to_grayscale(self, img: np.ndarray) -> np.ndarray:
        """Convert to grayscale"""
        if len(img.shape) == 2:
            return img
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    def _enhance_brightness(self, img: np.ndarray) -> np.ndarray:
        """
        Enhance brightness untuk gambar gelap
        """
        # Gamma correction
        gamma = 1.5
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255
                         for i in np.arange(0, 256)]).astype("uint8")
        
        return cv2.LUT(img, table)
    
    def _sharpen(self, img: np.ndarray) -> np.ndarray:
        """
        Sharpen untuk gambar blur
        """
        # Unsharp masking
        gaussian = cv2.GaussianBlur(img, (0, 0), 2.0)
        sharpened = cv2.addWeighted(img, 1.5, gaussian, -0.5, 0)
        return sharpened
    
    def _enhance_contrast(self, img: np.ndarray) -> np.ndarray:
        """
        CLAHE untuk low contrast images
        """
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        return clahe.apply(img)
    
    def _deskew(self, img: np.ndarray) -> np.ndarray:
        """
        Auto-detect dan fix skew
        Improved: lebih robust untuk berbagai kondisi
        """
        # Try edge detection
        edges = cv2.Canny(img, 50, 150, apertureSize=3)
        
        # Detect lines
        lines = cv2.HoughLinesP(
            edges, 
            1, 
            np.pi / 180, 
            threshold=100,
            minLineLength=img.shape[1] // 4,
            maxLineGap=20
        )
        
        if lines is None or len(lines) < 5:
            return img
        
        # Calculate angles
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            
            # Normalize angle to [-45, 45]
            if angle < -45:
                angle = 90 + angle
            elif angle > 45:
                angle = angle - 90
            
            angles.append(angle)
        
        # Median angle
        median_angle = np.median(angles)
        
        # Skip if already straight
        if abs(median_angle) < 0.5:
            return img
        
        # Rotate
        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        
        rotated = cv2.warpAffine(
            img, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=255
        )
        
        logger.debug(f"Deskew angle: {median_angle:.2f}°")
        return rotated
    
    def _denoise(self, img: np.ndarray, strength: int = 7) -> np.ndarray:
        """
        Advanced denoising
        """
        # Non-local Means Denoising
        denoised = cv2.fastNlMeansDenoising(
            img,
            h=strength,
            templateWindowSize=7,
            searchWindowSize=21
        )
        return denoised
    
    def _adaptive_binarize(self, img: np.ndarray) -> np.ndarray:
        """
        Adaptive binarization - try multiple methods and choose best
        """
        methods = []
        
        # Method 1: Adaptive Gaussian
        gaussian = cv2.adaptiveThreshold(
            img, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=15,
            C=3
        )
        methods.append(('gaussian', gaussian))
        
        # Method 2: Otsu's
        _, otsu = cv2.threshold(
            img, 0, 255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        methods.append(('otsu', otsu))
        
        # Method 3: Adaptive Mean
        mean_adaptive = cv2.adaptiveThreshold(
            img, 255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY,
            blockSize=15,
            C=3
        )
        methods.append(('mean', mean_adaptive))
        
        # Method 4: Sauvola (via local mean/std)
        sauvola = self._sauvola_threshold(img)
        methods.append(('sauvola', sauvola))
        
        # Choose best based on foreground ratio
        best_method = None
        best_score = float('inf')
        
        for name, binary in methods:
            ratio = self._foreground_ratio(binary)
            
            # Ideal ratio: 15-40% (text on white background)
            score = abs(ratio - 0.275)  # Target 27.5%
            
            if score < best_score and 0.10 < ratio < 0.50:
                best_score = score
                best_method = (name, binary)
        
        if best_method:
            logger.debug(f"Best binarization method: {best_method[0]}")
            return best_method[1]
        
        # Fallback: Gaussian
        return gaussian
    
    def _sauvola_threshold(self, img: np.ndarray, window_size: int = 15, k: float = 0.2) -> np.ndarray:
        """
        Sauvola's binarization - good for varying illumination
        """
        # Calculate local mean and std
        mean = cv2.boxFilter(img, cv2.CV_32F, (window_size, window_size))
        sqmean = cv2.boxFilter(img ** 2, cv2.CV_32F, (window_size, window_size))
        std = np.sqrt(sqmean - mean ** 2)
        
        # Sauvola threshold
        threshold = mean * (1 + k * ((std / 128.0) - 1))
        
        binary = np.where(img > threshold, 255, 0).astype(np.uint8)
        return binary
    
    def _foreground_ratio(self, binary: np.ndarray) -> float:
        """Calculate foreground pixel ratio"""
        return float(cv2.countNonZero(binary)) / float(binary.size)
    
    def _sauvola_threshold(self, img: np.ndarray, window_size: int = 15, k: float = 0.2) -> np.ndarray:
        """
        Sauvola's binarization - good for varying illumination
        ✅ FIX: Handle negative variance from floating point errors
        """
        # Convert to float32 untuk menghindari precision issues
        img_float = img.astype(np.float32)
        
        # Calculate local mean and std
        mean = cv2.boxFilter(img_float, cv2.CV_32F, (window_size, window_size))
        sqmean = cv2.boxFilter(img_float ** 2, cv2.CV_32F, (window_size, window_size))
        
        # ✅ FIX: Clip variance to avoid negative values from floating point errors
        variance = sqmean - mean ** 2
        variance = np.maximum(variance, 0)  # Force non-negative
        std = np.sqrt(variance)
        
        # Sauvola threshold
        threshold = mean * (1 + k * ((std / 128.0) - 1))
        
        binary = np.where(img > threshold, 255, 0).astype(np.uint8)
        return binary
    def _morphology(self, img: np.ndarray) -> np.ndarray:
        """
        Morphological operations - clean up noise
        """
        # Remove small noise
        kernel_small = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        opened = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel_small, iterations=1)
        
        # Connect broken text
        kernel_medium = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 1))
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel_medium, iterations=1)
        
        return closed