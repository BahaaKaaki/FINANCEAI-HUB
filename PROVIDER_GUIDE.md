# LLM Provider Guide

## 🚀 **Available Providers**

Our modular AI system supports multiple LLM providers. You can easily switch between them or add new ones.

### **Currently Supported:**

| Provider | Models | API Format | Status |
|----------|--------|------------|--------|
| **OpenAI** | GPT-4o, GPT-4o-mini | Native OpenAI | ✅ Ready |
| **Groq** | LLaMA, GPT-OSS | OpenAI-compatible | ✅ Ready |
| **Anthropic** | Claude 3.5 Haiku | Native Anthropic | ✅ Ready* |

*Requires `pip install anthropic`

## 🔧 **Configuration**

### **1. OpenAI Setup**
```env
DEFAULT_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_MODEL=gpt-4o-mini
```

### **2. Groq Setup** 
```env
DEFAULT_LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your-groq-key-here
GROQ_MODEL=openai/gpt-oss-20b
```

### **3. Anthropic Setup**
```env
DEFAULT_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
ANTHROPIC_MODEL=claude-3-5-haiku-20241022
```

## 📦 **Installation Requirements**

### **Base Requirements (Always Needed):**
```bash
pip install openai  # Used by OpenAI and Groq providers
```

### **Optional Dependencies:**
```bash
pip install anthropic  # For Anthropic Claude support
```

## 🎯 **Provider Features**

### **OpenAI Provider**
- ✅ Native OpenAI API
- ✅ GPT-4o, GPT-4o-mini models
- ✅ Function calling support
- ✅ Streaming support (future)

### **Groq Provider** 
- ✅ Ultra-fast inference (~450+ tokens/sec)
- ✅ OpenAI-compatible API
- ✅ LLaMA and GPT-OSS models
- ✅ Cost-effective alternative

### **Anthropic Provider**
- ✅ Claude 3.5 Haiku model
- ✅ Native Anthropic API format
- ✅ Advanced reasoning capabilities
- ✅ Tool calling support
- ✅ Message format conversion

## 🔄 **Switching Providers**

### **Runtime Switching:**
```python
from app.ai.providers import get_provider_class

# Get any provider
openai_provider = get_provider_class("openai")
groq_provider = get_provider_class("groq") 
anthropic_provider = get_provider_class("anthropic")

# Initialize with custom config
provider = openai_provider(
    api_key="your-key",
    model="gpt-4o-mini",
    temperature=0.1
)
```

### **Configuration Switching:**
Just change your `.env` file:
```env
# Switch from OpenAI to Groq
DEFAULT_LLM_PROVIDER=groq
```

## 🛠️ **Adding New Providers**

### **Step 1: Create Provider Class**
```python
# app/ai/providers/your_provider.py
from app.ai.providers.base import BaseLLMProvider
from app.ai.models import LLMResponse

class YourProvider(BaseLLMProvider):
    def chat_completion(self, messages, tools=None):
        # Your implementation here
        pass
    
    def validate_configuration(self):
        return bool(self.api_key)
    
    def get_provider_name(self):
        return "your_provider"
```

### **Step 2: Register Provider**
```python
# app/ai/providers/__init__.py
from .your_provider import YourProvider

PROVIDERS = {
    "openai": OpenAIProvider,
    "groq": GroqProvider,
    "anthropic": AnthropicProvider,
    "your_provider": YourProvider,  # Add here
}
```

### **Step 3: Add Configuration**
```python
# app/core/config.py
YOUR_PROVIDER_API_KEY: Optional[str] = Field(default=None)
YOUR_PROVIDER_MODEL: str = Field(default="default-model")
```

### **Step 4: Update LLM Client**
```python
# app/ai/llm_client.py
elif provider_name == "your_provider":
    self._provider = provider_class(
        api_key=self.settings.YOUR_PROVIDER_API_KEY,
        model=self.settings.YOUR_PROVIDER_MODEL,
        # ... other config
    )
```

## 🎉 **Benefits of Modular System**

### **✅ Easy Provider Management**
- Switch providers with one config change
- Test different models easily
- Fallback to different providers

### **✅ Cost Optimization**
- Use Groq for speed
- Use OpenAI for quality
- Use Anthropic for reasoning

### **✅ Future-Proof**
- Add new providers easily
- No breaking changes
- Extensible architecture

### **✅ Development Friendly**
- Mock providers for testing
- Provider-specific optimizations
- Clean separation of concerns

## 🚀 **Recommended Usage**

### **For Development:**
```env
DEFAULT_LLM_PROVIDER=groq  # Fast and cost-effective
```

### **For Production:**
```env
DEFAULT_LLM_PROVIDER=openai  # Reliable and well-tested
```

### **For Advanced Reasoning:**
```env
DEFAULT_LLM_PROVIDER=anthropic  # Claude's reasoning capabilities
```

## 📊 **Performance Comparison**

| Provider | Speed | Cost | Quality | Tool Support |
|----------|-------|------|---------|--------------|
| OpenAI | Medium | High | Excellent | ✅ Native |
| Groq | Very Fast | Low | Good | ✅ Compatible |
| Anthropic | Medium | Medium | Excellent | ✅ Native |

Choose based on your specific needs! 🎯