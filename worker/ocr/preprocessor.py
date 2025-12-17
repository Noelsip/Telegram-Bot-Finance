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
        denoise_strength: int = 7,
        use_clahe: bool = True,
        clahe_clip_limit: float = 2.0,
        clahe_tile_size: int = 8,
        apply_sharpen: bool = True,
        enable_binarize: bool = False,
        enable_morphology: bool = False
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
        self.use_clahe = use_clahe
        self.clahe_clip_limit = clahe_clip_limit
        self.clahe_tile_size = clahe_tile_size
        self.apply_sharpen = apply_sharpen
        self.enable_binarize = enable_binarize
        self.enable_morphology = enable_morphology
        
    def preprocess(self, img: np.ndarray) -> np.ndarray:
        """
        Preprocess image untuk OCR(main pipeline).
        
        Args:
            img (np.ndarray): Input image dalam format opencv (BGR).
            
        Returns:
            np.ndarray: Preprocessed image siap untuk OCR.
        """
        logger.info(f"Starting preprocessing, input shape: {img.shape}")
        
        # Resize jika terlalu besar
        img = self._resize(img) 
        logger.info(f"After resize, shape: {img.shape}")
        
        # Convert ke grayscale
        gray = self._to_grayscale(img)
        logger.info(f"After grayscale conversion, shape: {gray.shape}")
        
        if self.use_clahe:
            gray = self._enhance_contrast(gray)
            logger.info("After contrast enhancement (CLAHE)")

        if self.apply_sharpen:
            gray = self._sharpen(gray)
            logger.info("After sharpening")
        
        # Deskewing(luruskan)
        if self.auto_deskew:
            gray = self._deskew(gray)
            logger.info("After deskewing")
            
        # Denoising
        if self.denoise:
            gray = self._denoise(gray)
            logger.info("After denoising")
        
        # Binarization (opsional)
        if self.enable_binarize:
            binary = self._binarize(gray)
            logger.info("After binarization")
        else:
            binary = gray
            logger.info("Skip binarization (using grayscale image)")
        
        # Morphological operations (clean up, opsional)
        if self.enable_morphology and self.enable_binarize:
            result = self._morphology(binary)
            logger.info("After morphological operations")
        else:
            result = binary
            logger.info("Skip morphology (using pre-binarization image)")
        
        logger.info("Preprocessing completed")
        
        return result
    
    def _resize(self, img: np.ndarray) -> np.ndarray:
        """
        Resize image jika terlalu besar ATAU terlalu kecil.
        Upscale gambar kecil untuk OCR yang lebih baik.
        """
        MIN_HEIGHT = 800  # Minimum height untuk OCR yang baik
        h, w = img.shape[:2]
        
        # UPSCALE jika gambar terlalu kecil
        if h < MIN_HEIGHT:
            scale = MIN_HEIGHT / h
            new_w = int(w * scale)
            new_h = MIN_HEIGHT
            logger.info(f" Upscaling small image from {w}x{h} to {new_w}x{new_h}")
            return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        
        # DOWNSCALE jika gambar terlalu besar
        if w <= self.max_width and h <= self.max_height:
            return img
        
        # Kalkulasi scale ratio
        scale = min(self.max_width / w, self.max_height / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        logger.info(f" Downscaling large image from {w}x{h} to {new_w}x{new_h}")
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

    def _enhance_contrast(self, img: np.ndarray) -> np.ndarray:
        clahe = cv2.createCLAHE(
            clipLimit=self.clahe_clip_limit,
            tileGridSize=(self.clahe_tile_size, self.clahe_tile_size)
        )
        
        return clahe.apply(img)

    def _sharpen(self, img: np.ndarray) -> np.ndarray:
        kernel = np.array([
            [0, -1, 0],
            [-1, 5, -1],
            [0, -1, 0]
        ], dtype=np.float32)
        return cv2.filter2D(img, -1, kernel)
    
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
        # Adaptive Gaussian thresholding
        gaussian = cv2.adaptiveThreshold(
            img,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=15,
            C=3,
        )

        # Otsu's method (cocok untuk pencahayaan cukup merata)
        _, otsu = cv2.threshold(
            img,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )

        def foreground_ratio(binary: np.ndarray) -> float:
            return float(cv2.countNonZero(binary)) / float(binary.size)

        ratio_gauss = foreground_ratio(gaussian)
        ratio_otsu = foreground_ratio(otsu)

        # Pilih hasil dengan rasio foreground yang "sehat"
        if 0.15 < ratio_gauss < 0.85:
            return gaussian
        if 0.15 < ratio_otsu < 0.85:
            return otsu

        # Fallback: gunakan Gaussian sebagai default
        return gaussian
     
    def _morphology(self, img: np.ndarray) -> np.ndarray:
        """
        Apply morphological operations untuk bersihkan image
        
        Methode: 
        - Opening: Remove small noise
        - Closing: Fill small gaps
        """
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        opened = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel, iterations=1)
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel, iterations=1)
        return closed