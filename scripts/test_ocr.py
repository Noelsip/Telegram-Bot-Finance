"""
Test OCR Implementation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test script untuk verify OCR pipeline:
1. Test preprocessing
2. Test Tesseract
3. Test full pipeline
"""

import sys
import os
import logging
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker.services.ocr_service import OCRService
from worker.utils.image_utils import load_image, get_image_info

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_ocr_with_sample():
    """
    Test OCR dengan sample image
    """
    print("=" * 60)
    print("OCR TESTING")
    print("=" * 60)
    
    # Path ke sample receipt (you need to provide this)
    sample_image_path = "upload/receipts/struk.jpg"
    
    # Check if sample exists
    if not os.path.exists(sample_image_path):
        print(f"\n⚠️  Sample image not found: {sample_image_path}")
        print("   Please place a receipt image at this location to test OCR")
        return False
    
    print(f"\n📄 Testing with: {sample_image_path}")
    
    try:
        # Initialize OCR service
        print("\n🔧 Initializing OCR Service...")
        ocr_service = OCRService(
            save_preprocessed=True,  # Save preprocessed untuk debugging
            preprocessed_dir="upload/temp"
        )
        
        # Process image
        print("\n🔍 Processing image...")
        text, metadata = ocr_service.process_image(sample_image_path)
        
        # Display results
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        
        print(f"\n📊 Metadata:")
        print(f"   Confidence: {metadata['confidence']:.2f}%")
        print(f"   Word Count: {metadata['word_count']}")
        print(f"   Char Count: {metadata['char_count']}")
        print(f"   Line Count: {metadata['line_count']}")
        print(f"   Processing Time: {metadata['processing_time_ms']}ms")
        print(f"   Image Size: {metadata['original_width']}x{metadata['original_height']}")
        print(f"   Preprocessing Steps: {', '.join(metadata['preprocessing_steps'])}")
        
        print(f"\n📝 Extracted Text:")
        print("-" * 60)
        print(text)
        print("-" * 60)
        
        # Quality check
        print(f"\n🎯 Quality Assessment:")
        if metadata['confidence'] >= 80:
            print("   ✅ EXCELLENT - High confidence OCR")
        elif metadata['confidence'] >= 60:
            print("   ⚠️  GOOD - Acceptable confidence")
        else:
            print("   ❌ POOR - Low confidence, may need manual review")
        
        if metadata['word_count'] > 10:
            print("   ✅ Good amount of text detected")
        else:
            print("   ⚠️  Low word count - image may be unclear")
        
        print("\n✅ OCR test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ OCR test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_preprocessing_only():
    """
    Test preprocessing tanpa OCR
    """
    print("\n" + "=" * 60)
    print("PREPROCESSING TEST")
    print("=" * 60)
    
    sample_image_path = "upload/receipts/sample_receipt.jpg"
    
    if not os.path.exists(sample_image_path):
        print(f"\n⚠️  Sample image not found: {sample_image_path}")
        return False
    
    try:
        from worker.ocr.preprocessor import ImagePreprocessor
        
        print("\n🔧 Testing preprocessing pipeline...")
        
        # Load image
        img = load_image(sample_image_path)
        img_info = get_image_info(img)
        
        print(f"\n📷 Original Image:")
        print(f"   Size: {img_info['width']}x{img_info['height']}")
        print(f"   Channels: {img_info['channels']}")
        print(f"   Size: {img_info['size_kb']:.2f} KB")
        
        # Preprocess
        preprocessor = ImagePreprocessor()
        preprocessed = preprocessor.preprocess(img)
        
        processed_info = get_image_info(preprocessed)
        
        print(f"\n🔧 Preprocessed Image:")
        print(f"   Size: {processed_info['width']}x{processed_info['height']}")
        print(f"   Channels: {processed_info['channels']}")
        print(f"   Size: {processed_info['size_kb']:.2f} KB")
        
        # Save preprocessed
        from worker.utils.image_utils import save_image
        output_path = "upload/temp/preprocessed_test.jpg"
        save_image(preprocessed, output_path)
        
        print(f"\n💾 Preprocessed image saved: {output_path}")
        print("✅ Preprocessing test passed!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Preprocessing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """
    Run all OCR tests
    """
    print("\n🧪 Starting OCR Tests...\n")
    
    # Test 1: Preprocessing only
    test1_passed = test_preprocessing_only()
    
    # Test 2: Full OCR pipeline
    test2_passed = test_ocr_with_sample()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Preprocessing Test: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"OCR Pipeline Test:  {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! OCR implementation is ready.")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main()