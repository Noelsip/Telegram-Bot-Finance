"""
Image Utility Functions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Helper functions untuk image processing.
"""

import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional
import os

def load_image(path: str) -> np.ndarray:
    """
    Load image dari file path
    
    Args:
        path: Path ke file gambar
        
    Returns:
        np.ndarray: Image dalam format OpenCV (BGR)
        
    Raises:
        FileNotFoundError: Jika file tidak ditemukan
        ValueError: Jika file bukan gambar valid
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Image file not found: {path}")
    
    img = cv2.imread(path)
    
    if img is None:
        raise ValueError(f"Failed to load image: {path}")
    
    return img

def save_image(img: np.ndarray, path: str) -> None:  # ✅ FIXED: parameter order
    """
    Save image ke file
    
    Args:
        img: Image array (OpenCV format)
        path: Path output file
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cv2.imwrite(path, img)

def resize_image(img: np.ndarray, max_width: int = 1920, max_height: int = 1080) -> np.ndarray:
    """
    Resize image jika terlalu besar
    """
    h, w = img.shape[:2]
    
    if w <= max_width and h <= max_height:
        return img
    
    scale = min(max_width / w, max_height / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return resized

def to_grayscale(img: np.ndarray) -> np.ndarray:
    """
    Convert image ke grayscale
    """
    if len(img.shape) == 2:
        return img
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return gray

def pil_to_cv(pil_img: Image.Image) -> np.ndarray: 
    """
    Convert PIL Image ke OpenCV format
    """
    img_array = np.array(pil_img)
    
    if len(img_array.shape) == 3 and img_array.shape[2] == 3:
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    else:
        img_bgr = img_array
    
    return img_bgr

def cv_to_pil(cv_img: np.ndarray) -> Image.Image: 
    """
    Convert OpenCV image ke PIL format
    """
    if len(cv_img.shape) == 3 and cv_img.shape[2] == 3:
        img_rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    else:
        img_rgb = cv_img
    
    pil_img = Image.fromarray(img_rgb)
    return pil_img

def get_image_info(img: np.ndarray) -> dict: 
    """
    Get informasi tentang image
    """
    h, w = img.shape[:2]
    channels = img.shape[2] if len(img.shape) == 3 else 1
    
    return {
        "width": w,
        "height": h,
        "channels": channels,
        "dtype": str(img.dtype),
        "size_kb": img.nbytes / 1024
    }