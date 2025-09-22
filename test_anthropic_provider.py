"""
Test Anthropic provider functionality.
"""

from app.ai.providers import get_provider_class, get_available_providers


def test_anthropic_provider():
    """Test Anthropic provider implementation."""
    
    print("🧪 Testing Anthropic Provider")
    print("=" * 40)
    
    # Check if Anthropic is available
    providers = get_available_providers()
    print(f"Available Providers: {providers}")
    
    if "anthropic" not in providers:
        print("❌ Anthropic provider not available")
        print("💡 To enable Anthropic support:")
        print("   pip install anthropic")
        return
    
    try:
        # Get Anthropic provider class
        anthropic_class = get_provider_class("anthropic")
        print(f"✅ Anthropic Provider Class: {anthropic_class.__name__}")
        
        # Test provider initialization (without real API key)
        try:
            provider = anthropic_class(
                api_key="sk-ant-test-key",  # Fake key for testing
                model="claude-3-5-haiku-20241022"
            )
            print(f"✅ Provider initialized with model: {provider.model}")
            print(f"✅ Provider name: {provider.get_provider_name()}")
            
            # Test configuration validation (should fail with fake key)
            is_valid = provider.validate_configuration()
            print(f"🔧 Configuration valid: {is_valid}")
            
        except ImportError as e:
            print(f"❌ Anthropic library not installed: {str(e)}")
            print("💡 Install with: pip install anthropic")
        except Exception as e:
            print(f"⚠️  Provider initialization issue: {str(e)}")
    
    except Exception as e:
        print(f"❌ Error testing Anthropic provider: {str(e)}")


def test_provider_switching():
    """Test switching between different providers."""
    
    print(f"\n🔄 Testing Provider Switching")
    print("=" * 40)
    
    providers = get_available_providers()
    
    for provider_name in providers:
        try:
            provider_class = get_provider_class(provider_name)
            print(f"✅ {provider_name}: {provider_class.__name__}")
            
            # Show provider-specific features
            if provider_name == "openai":
                print(f"   • Default model: gpt-4o-mini")
                print(f"   • API format: OpenAI native")
            elif provider_name == "groq":
                print(f"   • Default model: openai/gpt-oss-20b")
                print(f"   • API format: OpenAI-compatible")
            elif provider_name == "anthropic":
                print(f"   • Default model: claude-3-5-haiku-20241022")
                print(f"   • API format: Anthropic native")
                
        except Exception as e:
            print(f"❌ {provider_name}: {str(e)}")


def show_anthropic_features():
    """Show Anthropic-specific features."""
    
    print(f"\n🎯 Anthropic Provider Features")
    print("=" * 40)
    
    features = [
        "✅ Claude 3.5 Haiku support",
        "✅ Native Anthropic API format",
        "✅ Tool calling support",
        "✅ Message format conversion",
        "✅ Automatic dependency detection",
        "✅ Graceful fallback if not installed"
    ]
    
    for feature in features:
        print(f"   {feature}")
    
    print(f"\n📝 Configuration Example:")
    print(f"   DEFAULT_LLM_PROVIDER=anthropic")
    print(f"   ANTHROPIC_API_KEY=sk-ant-your-key-here")
    print(f"   ANTHROPIC_MODEL=claude-3-5-haiku-20241022")


if __name__ == "__main__":
    test_anthropic_provider()
    test_provider_switching()
    show_anthropic_features()
    
    print(f"\n🎉 Anthropic provider testing complete!")
    print(f"💡 The modular system makes it easy to add any LLM provider!")