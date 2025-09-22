"""
Test script to verify Groq API key is working.
"""

import os
import requests
import json

def test_groq_key():
    """Test if the Groq API key is valid."""
    
    # Load API key from .env
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("❌ No GROQ_API_KEY found in environment")
        return False
    
    print(f"🔑 Testing Groq API key: {api_key[:20]}...")
    
    try:
        # Groq API endpoint
        url = "https://api.groq.com/openai/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Test payload with current model
        payload = {
            "model": "openai/gpt-oss-20b",  # OpenAI GPT-OSS model on Groq
            "messages": [
                {"role": "user", "content": "Say 'Hello, Groq API key is working!'"}
            ],
            "max_tokens": 50,
            "temperature": 0.1
        }
        
        print("🚀 Making test request to Groq API...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            message = data['choices'][0]['message']['content']
            print("✅ Groq API key is valid!")
            print(f"Response: {message}")
            print(f"Model used: {data.get('model', 'unknown')}")
            return True
        else:
            print(f"❌ API request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
    except Exception as e:
        print(f"❌ Groq API test failed: {str(e)}")
        
        # Check for specific error types
        error_str = str(e).lower()
        if "401" in error_str or "unauthorized" in error_str:
            print("\n💡 This looks like an invalid API key error.")
            print("   To fix this:")
            print("   1. Go to https://console.groq.com/keys")
            print("   2. Create a new API key")
            print("   3. Replace the GROQ_API_KEY in your .env file")
        elif "quota" in error_str or "rate_limit" in error_str:
            print("\n💡 Rate limit or quota issue.")
            print("   Check your Groq account usage limits.")
        
        return False

def test_groq_models():
    """Test available Groq models."""
    
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("❌ No API key available for model testing")
        return False
    
    print(f"\n🤖 Testing available Groq models...")
    
    try:
        url = "https://api.groq.com/openai/v1/models"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            models = data.get('data', [])
            
            print(f"✅ Found {len(models)} available models:")
            for model in models[:10]:  # Show first 10 models
                print(f"   - {model.get('id', 'unknown')}")
            
            if len(models) > 10:
                print(f"   ... and {len(models) - 10} more models")
            
            return True
        else:
            print(f"❌ Models request failed: {response.status_code}")
            return False
        
    except Exception as e:
        print(f"❌ Models test failed: {str(e)}")
        return False

def test_specific_models():
    """Test specific Groq models that work well for our use case."""
    
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        return False
    
    # Current Groq models to test (as of 2024)
    models_to_test = [
        "llama-3.1-8b-instant", 
        "llama-3.2-1b-preview",
        "llama-3.2-3b-preview",
        "mixtral-8x7b-32768",
        "gemma2-9b-it"
    ]
    
    print(f"\n🧪 Testing specific models...")
    
    working_models = []
    
    for model in models_to_test:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "max_tokens": 10,
                "temperature": 0.1
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            
            if response.status_code == 200:
                print(f"   ✅ {model} - Working")
                working_models.append(model)
            else:
                print(f"   ❌ {model} - Failed ({response.status_code})")
                
        except Exception as e:
            print(f"   ❌ {model} - Error: {str(e)[:50]}...")
    
    if working_models:
        print(f"\n🎉 Recommended model for your .env: {working_models[0]}")
        return working_models[0]
    
    return None

if __name__ == "__main__":
    print("🧪 Groq API Key Test")
    print("=" * 40)
    
    # Test API key
    key_valid = test_groq_key()
    
    # Test models if key is valid
    if key_valid:
        test_groq_models()
        recommended_model = test_specific_models()
        
        if recommended_model:
            print(f"\n📝 To use Groq in your system:")
            print(f"   1. Add to your .env file:")
            print(f"      DEFAULT_LLM_PROVIDER=groq")
            print(f"      GROQ_MODEL={recommended_model}")
            print(f"   2. Update your LLM client to support Groq")
    
    print("\n" + "=" * 40)
    if key_valid:
        print("🎉 Groq API key is working!")
    else:
        print("⚠️  Please fix the API key issue and try again.")