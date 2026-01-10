# test_intent_classifier.py
import asyncio
from worker.llm.intent_classifier import classify_intent, UserIntent

async def test_classification():
    """Test various user inputs"""
    
    test_cases = [
        # Transactions
        ("beli makan 25rb", UserIntent.TRANSACTION),
        ("gaji masuk 5jt", UserIntent.TRANSACTION),
        ("bayar listrik 350rb", UserIntent.TRANSACTION),
        
        # Help
        ("help", UserIntent.HELP),
        ("cara pakai bot ini", UserIntent.HELP),
        ("gimana nggunainnya", UserIntent.HELP),
        
        # History
        ("lihat transaksi hari ini", UserIntent.HISTORY),
        ("history minggu ini", UserIntent.HISTORY),
        ("rekap bulan ini", UserIntent.HISTORY),
        
        # Export
        ("kirim excel", UserIntent.EXPORT),
        ("download laporan", UserIntent.EXPORT),
        
        # Small talk
        ("hai", UserIntent.SMALL_TALK),
        ("terima kasih", UserIntent.SMALL_TALK),
        ("mantap", UserIntent.SMALL_TALK),
    ]
    
    print("=" * 70)
    print("INTENT CLASSIFICATION TESTS")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for text, expected_intent in test_cases:
        result = await classify_intent(text)
        detected_intent = result["intent"]
        confidence = result["confidence"]
        reasoning = result["reasoning"]
        
        status = "✅ PASS" if detected_intent == expected_intent else "❌ FAIL"
        
        if detected_intent == expected_intent:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{status}")
        print(f"Input: '{text}'")
        print(f"Expected: {expected_intent.value}")
        print(f"Detected: {detected_intent.value}")
        print(f"Confidence: {confidence:.2f}")
        print(f"Reasoning: {reasoning}")
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_classification())