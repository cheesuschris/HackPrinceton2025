"""Test the prompts with LLM."""
import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from services.llm import call_llm
from agents.prompts import system_prompt, initial_user_message


def main():
    # Test product info
    brand = "Patagonia"
    product_name = "Nano Puff Jacket"
    
    # Test with empty search history
    print("=" * 60)
    print("Test 1: Empty search history")
    print("=" * 60)
    
    prompt = system_prompt(brand, product_name, [])
    print("\nSystem Prompt:")
    print(prompt)
    print("\n" + "-" * 60)
    
    print("\nCalling LLM...")
    try:
        result = call_llm(prompt, model="gemini-2.5-flash-lite", temperature=0.2, max_tokens=200)
        print("\nLLM Response:")
        print(result)
    except Exception as e:
        print(f"Error: {e}")
    
    # Test with search history
    print("\n\n" + "=" * 60)
    print("Test 2: With search history")
    print("=" * 60)
    
    search_history = [
        {"query": f"{brand} {product_name} carbon footprint", "result": "Found information about carbon footprint..."},
        {"query": f"{brand} sustainability", "result": "Brand has good sustainability practices..."}
    ]
    
    prompt = system_prompt(brand, product_name, search_history)
    print("\nSystem Prompt:")
    print(prompt)
    print("\n" + "-" * 60)
    
    print("\nCalling LLM...")
    try:
        result = call_llm(prompt, model="gemini-2.5-flash-lite", temperature=0.2, max_tokens=200)
        print("\nLLM Response:")
        print(result)
    except Exception as e:
        print(f"Error: {e}")
    
    # Test initial user message
    print("\n\n" + "=" * 60)
    print("Test 3: Initial user message")
    print("=" * 60)
    
    user_msg = initial_user_message(brand, product_name)
    print(f"\nInitial User Message: {user_msg}")


if __name__ == "__main__":
    main()

