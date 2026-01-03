"""
Test OpenAI API Connection
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from worker.llm.llm_client import call_llm, LLMAPIError

def test_openai():
    print("🧪 Testing OpenAI API Connection...\n")
    
    try:
        # Test prompt
        test_prompt = """
        Parse this transaction:
        "Beli makan siang di warteg 25000"
        """
        
        print(f"📝 Prompt: {test_prompt.strip()}")
        print("\n⏳ Calling OpenAI API...\n")
        
        # Call LLM
        result = call_llm(test_prompt)
        
        # Print result
        print("✅ SUCCESS!")
        print(f"\n📊 Model: {result['model']}")
        print(f"📈 Token Usage: {result['usage']}")
        print(f"\n💬 Response:\n{result['text']}\n")
        
        return True
        
    except LLMAPIError as e:
        print(f"❌ LLM API Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_openai()
    sys.exit(0 if success else 1)