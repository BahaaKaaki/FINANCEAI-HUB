"""
Test script to verify OpenAI API key is working.
"""

import os
from openai import OpenAI

def test_openai_key():
    """Test if the OpenAI API key is valid."""
    
    # Load API key from .env
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ No OPENAI_API_KEY found in environment")
        return False
    
    print(f"🔑 Testing API key: {api_key[:20]}...")
    
    try:
        client = OpenAI(api_key=api_key)
        
        # Make a simple test request
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Say 'Hello, API key is working!'"}
            ],
            max_tokens=20
        )
        
        print("✅ API key is valid!")
        print(f"Response: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ API key test failed: {str(e)}")
        
        # Check for specific error types
        error_str = str(e).lower()
        if "401" in error_str or "invalid_api_key" in error_str or "incorrect api key" in error_str:
            print("\n💡 This looks like an invalid API key error.")
            print("   To fix this:")
            print("   1. Go to https://platform.openai.com/account/api-keys")
            print("   2. Create a new API key")
            print("   3. Replace the OPENAI_API_KEY in your .env file")
            print("   4. Make sure you have credits in your OpenAI account")
        elif "quota" in error_str or "billing" in error_str:
            print("\n💡 This looks like a billing/quota issue.")
            print("   Check your OpenAI account billing and usage limits.")
        elif "rate_limit" in error_str:
            print("\n💡 Rate limit exceeded. Wait a moment and try again.")
        
        return False

def test_model_availability():
    """Test if the configured model is available."""
    
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    if not api_key:
        print("❌ No API key available for model testing")
        return False
    
    print(f"\n🤖 Testing model availability: {model}")
    
    try:
        client = OpenAI(api_key=api_key)
        
        # Test the specific model
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "Test"}
            ],
            max_tokens=5
        )
        
        print(f"✅ Model {model} is available and working!")
        return True
        
    except Exception as e:
        print(f"❌ Model test failed: {str(e)}")
        
        if "model" in str(e).lower():
            print(f"\n💡 Model '{model}' might not be available.")
            print("   Try using one of these models instead:")
            print("   - gpt-4o-mini (recommended, cost-effective)")
            print("   - gpt-4o")
            print("   - gpt-3.5-turbo")
        
        return False

if __name__ == "__main__":
    print("🧪 OpenAI API Key Test")
    print("=" * 30)
    
    # Test API key
    key_valid = test_openai_key()
    
    # Test model if key is valid
    if key_valid:
        test_model_availability()
    
    print("\n" + "=" * 30)
    if key_valid:
        print("🎉 All tests passed! Your OpenAI setup is working.")
    else:
        print("⚠️  Please fix the API key issue and try again.")
        print("   The system will use mock mode until this is resolved.")