"""
================================================================================
FILE: worker/ocr/preprocessor.py
DESKRIPSI: Image Preprocessing untuk OCR
ASSIGNEE: @ML/Vision
PRIORITY: HIGH
SPRINT: 2
================================================================================

DEPENDENCIES:
- opencv-python (cv2)
- pillow (PIL)
- numpy

INSTALL: pip install opencv-python pillow numpy

TODO [OCR-PREP-001]: preprocess_image(file_path) -> str
Fungsi utama preprocessing. Return path ke processed image.

Langkah-langkah:
1. Load image dengan cv2.imread(file_path)
2. Convert ke grayscale: cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
3. Resize jika terlalu besar (max dimension 2000px)
4. Apply deskew jika image miring
5. Apply denoising
6. Apply adaptive thresholding
7. Save processed image ke temp file
8. Return path ke processed image

TODO [OCR-PREP-002]: convert_to_grayscale(image) -> np.ndarray
- Input: BGR image (numpy array)
- Output: Grayscale image

TODO [OCR-PREP-003]: resize_image(image, max_dimension=2000) -> np.ndarray
- Jika width atau height > max_dimension, resize proportionally
- Maintain aspect ratio

TODO [OCR-PREP-004]: deskew_image(image) -> np.ndarray
Straighten rotated/skewed images.

Teknik:
1. Detect lines menggunakan cv2.HoughLinesP
2. Calculate average angle of lines
3. Rotate image untuk straighten
4. Atau gunakan: cv2.minAreaRect pada contours

TODO [OCR-PREP-005]: denoise_image(image) -> np.ndarray
Hilangkan noise dari image.

Opsi:
- cv2.fastNlMeansDenoising() - bagus tapi lambat
- cv2.bilateralFilter() - preserve edges
- cv2.GaussianBlur() - simple tapi blur text juga

Rekomendasi: bilateralFilter dengan params (9, 75, 75)

TODO [OCR-PREP-006]: apply_threshold(image) -> np.ndarray
Buat image binary (hitam putih) untuk text clarity.

Opsi:
- cv2.threshold() - simple global threshold
- cv2.adaptiveThreshold() - lebih baik untuk uneven lighting (RECOMMENDED)

Params untuk adaptiveThreshold:
- cv2.ADAPTIVE_THRESH_GAUSSIAN_C
- cv2.THRESH_BINARY
- blockSize=11
- C=2

CATATAN:
- Semua fungsi menerima numpy array dan return numpy array
- preprocess_image adalah orchestrator yang memanggil fungsi lain
- Test dengan berbagai jenis struk (thermal, inkjet, foto HP)
================================================================================
"""
