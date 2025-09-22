"""
Test the new modular provider system.
"""

from app.ai.providers import get_available_providers, get_provider_class
from app.ai import get_llm_client


def test_provider_system():
    """Test the modular provider system."""
    
    print("🧪 Testing Modular Provider System")
    print("=" * 50)
    
    # Test available providers
    providers = get_available_providers()
    print(f"📋 Available Providers: {providers}")
    
    # Test provider classes
    for provider_name in providers:
        try:
            provider_class = get_provider_class(provider_name)
            print(f"✅ {provider_name}: {provider_class.__name__}")
        except Exception as e:
            print(f"❌ {provider_name}: {str(e)}")
    
    # Test LLM client with new provider system
    print(f"\n🔧 Testing LLM Client Integration:")
    try:
        client = get_llm_client()
        provider_info = client.get_provider_info()
        
        print(f"Current Provider: {provider_info['provider']}")
        print(f"Current Model: {provider_info['model']}")
        print(f"Configured: {provider_info['configured']}")
        print(f"Available: {provider_info['available_providers']}")
        
        if provider_info['configured']:
            print("✅ Provider system working correctly!")
        else:
            print("⚠️  Provider not configured (expected if no API keys)")
            
    except Exception as e:
        print(f"❌ LLM Client error: {str(e)}")


if __name__ == "__main__":
    test_provider_system()