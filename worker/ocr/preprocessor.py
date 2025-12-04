import cv2
import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class ImagePreprocessor:
    """
    Image preprocessor untuk OCR
    
    Pipeline:
    - Resize (jika terlalu besar)
    - Grayscale conversion
    - Deskew (Luruskan gambar miring)
    - Denoise (hilangkan noise)
    - Binarization (threshold hitam-putih)
    - Morphological operations (opsional)
    """
    
    def __init__(
        self,
        max_width: int = 1920,
        max_height: int = 1080,
        auto_deskew: bool = True,
        denoise: bool = True,
        denoise_strength: int = 7
    ):
        """
        Initialize preprocessor dengan parameter yang diberikan.
        
        Args:
            max_width (int): Maksimal lebar gambar.
            max_height (int): Maksimal tinggi gambar.
            auto_deskew (bool): Apakah melakukan deskewing.
            denoise (bool): Apakah melakukan denoising.
        """
        self.max_width = max_width
        self.max_height = max_height
        self.auto_deskew = auto_deskew
        self.denoise = denoise
        self.denoise_strength = denoise_strength
        
    def preprocess(self, img: np.ndarray) -> np.ndarray:
        """
        Preprocess image untuk OCR(main pipeline).
        
        Args:
            img (np.ndarray): Input image dalam format opencv (BGR).
            
        Returns:
            np.ndarray: Preprocessed image siap untuk OCR.
        """
        logger.info(f"Starting preprocessing, input shape: {img.shape}")
        
        # Step 1: Resize jika terlalu besar
        img = self._resize(img) 
        logger.info(f"After resize, shape: {img.shape}")
        
        # Step 2: Convert ke grayscale
        gray = self._to_grayscale(img)
        logger.info(f"After grayscale conversion, shape: {gray.shape}")
        
        # Step 3: Deskewing(luruskan)
        if self.auto_deskew:
            gray = self._deskew(gray)
            logger.info("After deskewing")
            
        # Step 4: Denoising
        if self.denoise:
            gray = self._denoise(gray)
            logger.info("After denoising")
        
        # Step 5: Binarization
        binary = self._binarize(gray)
        logger.info("After binarization")
        
        # Step 6: Morphological operations (clean up)
        result = self._morphology(binary)
        logger.info("After morphological operations")
        
        logger.info("Preprocessing completed")
        
        return result
    
    def _resize(self, img: np.ndarray) -> np.ndarray:
        """
        Resize image jika terlalu besar
        """
        h, w = img.shape[:2]
        
        if w <= self.max_width and h <= self.max_height:
            return img
        
        # Kalkulasi scale ratio
        scale = min(self.max_width / w, self.max_height / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        resized_img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized_img

    def _to_grayscale(self, img: np.ndarray) -> np.ndarray:
        """
        Convert image ke grayscale
        """
        if len(img.shape) == 2:
            return img
        
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return gray_img
    
    def _deskew(self, img: np.ndarray) -> np.ndarray:
        """
        Auto-detext dan fix skew(gambar miring)

        method: hough line transform
        - detect lines di image
        - calculate angle
        - rotate image
        """
        # Detect edges
        edges = cv2.Canny(img, 50, 150, apertureSize=3)
        
        # Detect lines menggunakan Hough Transform
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
        
        if lines is None:
            return img
        
        # calculasi median angle dari semua line
        angles = []
        for line in lines:
            rho, theta = line[0]
            angle = (theta * 180 / np.pi) - 90
            angles.append(angle)
            
        if not angles:
            return img
        
        # median angle
        median_angle = np.median(angles)
        
        # skip jika sudah lurus
        if abs(median_angle) < 0.5:
            return img
        
        # Rotate image untuk deskew
        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        
        # rotation matrix
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        
        # apply rotasi dengan white background
        rotated = cv2.warpAffine(
            img, M, (w, h), 
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=255
        )
        
        logger.debug(f"Deskew angle: {median_angle:.2f}")
        return rotated
    
    def _denoise(self, img: np.ndarray) -> np.ndarray:
        """
        Remove noise dari image

        metode: Non-local Means Denoising
        """
        
        denoised = cv2.fastNlMeansDenoising(
            img,
            h=self.denoise_strength,
            templateWindowSize=7,
            searchWindowSize=21
        )
        return denoised
    
    def _binarize(self, img: np.ndarray) -> np.ndarray:
        """
        Convert ke binary image (Hitam - putih)
        
        Methode: Adaptive gaussian thresholding
        """
        binary_gaussian = cv2.adaptiveThreshold(
            img,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=15,
            C=3
        )

        # Method 2: Otsu's method (for uniform lighting)
        _, binary_otsu = cv2.threshold(
            img,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        
        # Use Gaussian for rece
        return binary_gaussian
    
    def _morphology(self, img: np.ndarray) -> np.ndarray:
        """
        Apply morphological operations untuk bersihkan image
        
        Methode: 
        - Opening: Remove small noise
        - Closing: Fill small gaps
        """
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))

        
        opened = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel)

        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
        return closed