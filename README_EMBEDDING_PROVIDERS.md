# Embedding Provider Implementation

This implementation adds support for multiple embedding providers with a clean abstraction layer.

## Architecture

```
/app/services/embedding/
├── __init__.py          # Package exports
├── base.py              # BaseEmbeddingProvider protocol
├── openai_provider.py   # OpenAI-compatible API implementation
├── ollama_provider.py   # Ollama local API implementation
└── factory.py           # Provider factory with config-based selection
```

## Features

- **Provider Abstraction**: Clean protocol-based interface for embedding providers
- **Runtime Switching**: Configure provider via environment variable (no code changes)
- **Ollama Support**: Local embedding generation with bge-m3:567m model
- **OpenAI Compatible**: Works with OpenAI, GLM, and other compatible APIs
- **Backward Compatible**: Existing configurations continue to work
- **Graceful Degradation**: Handles errors and falls back appropriately
- **Performance Monitoring**: Logs timing metrics for comparison

## Configuration

### Environment Variables

```bash
# Provider Selection
LLM_EMBEDDING_PROVIDER=ollama  # "openai" or "ollama"

# OpenAI-Compatible Provider (when LLM_EMBEDDING_PROVIDER=openai)
OPENAI_EMBEDDING_BASE_URL=https://open.bigmodel.cn/api/paas/v4
OPENAI_EMBEDDING_MODEL=embedding-3
OPENAI_EMBEDDING_API_KEY=sk-your-api-key-here

# Ollama Provider (when LLM_EMBEDDING_PROVIDER=ollama)
OLLAMA_EMBEDDING_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=bge-m3:567m

# Shared Settings
LLM_EMBEDDING_BATCH_SIZE=64
LLM_EMBEDDING_RETRY_MAX_ATTEMPTS=5
LLM_EMBEDDING_RETRY_INITIAL_BACKOFF=1.0
```

### Backward Compatibility

Old configuration variables are still supported:

```bash
# These map to OpenAI provider settings
LLM_EMBEDDING_BASE_URL=...
LLM_EMBEDDING_MODEL=...
LLM_EMBEDDING_API_KEY=...
```

## Usage

### Using the Factory

```python
from app.services.embedding.factory import get_embedding_provider
from app.services.llm.client import LLMClient

# Create provider based on configuration
embedding_provider = get_embedding_provider()

# Inject into LLMClient
llm_client = LLMClient(embedding_provider=embedding_provider)

# Generate embeddings
embedding = await llm_client.generate_embedding("text")
embeddings = await llm_client.generate_embeddings_batch(["text1", "text2"])
```

### Direct Provider Usage

```python
from app.services.embedding.ollama_provider import OllamaEmbeddingProvider

provider = OllamaEmbeddingProvider(
    base_url="http://localhost:11434",
    model="bge-m3:567m",
    batch_size=64
)

embedding = await provider.generate_embedding("text")
embeddings = await provider.generate_embeddings_batch(["text1", "text2"])

await provider.close()
```

## Ollama Setup

### Installation

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Start service
ollama serve
```

### Pull Model

```bash
# Pull the bge-m3:567m model (1.1GB)
ollama pull bge-m3:567m

# Verify model is available
ollama list
```

### Verify Service

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Expected response:
# {"models":[{"name":"bge-m3:567m",...}]}
```

## Testing

### Test Ollama Provider

```bash
LLM_EMBEDDING_PROVIDER=ollama python demos/test_ollama_embedding.py
```

Expected output:
```
✅ Generated 5 embeddings in 0.18s
   Dimension: 1024
   Average: 0.04s per embedding
```

### Test Provider Comparison

```bash
python demos/test_provider_comparison.py
```

Compares performance, cost, and privacy between providers.

### Test with Real Data

```bash
# Set provider in .env
LLM_EMBEDDING_PROVIDER=ollama

# Run batch embedding test
python demos/test_batch_embedding.py
```

## Provider Comparison

| Feature | Ollama (Local) | OpenAI (Remote) |
|---------|---------------|-----------------|
| **Cost** | Free | Pay per request |
| **Speed** | Fast (local) | Network latency |
| **Privacy** | Data stays local | Data sent to API |
| **Availability** | Requires local setup | Always available |
| **Rate Limits** | None | Yes (429 errors) |
| **Model** | bge-m3:567m (1024d) | Configurable |
| **Setup** | Install Ollama + pull model | API key only |

## Performance Metrics

From testing with 5 texts:

- **Ollama**: 0.18s total (0.04s per embedding)
- **Network latency**: ~10ms (vs 100-500ms for remote)
- **Batch size**: Up to 64 items per request
- **No rate limits**: Process unlimited items

## Error Handling

### Ollama Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Connection refused | Ollama not running | Run `ollama serve` |
| Model not found | Model not pulled | Run `ollama pull bge-m3:567m` |
| Timeout | Model loading | Wait for first inference |

### OpenAI Errors

| Error | Cause | Solution |
|-------|-------|----------|
| HTTP 401 | Invalid API key | Check credentials |
| HTTP 429 | Rate limit | Automatic retry with backoff |
| HTTP 400 | Bad request | Graceful degradation |

## Migration Guide

### From Old Configuration

No code changes needed! Just set the provider:

```bash
# .env
LLM_EMBEDDING_PROVIDER=ollama  # Add this line

# Keep existing config for backward compatibility
LLM_EMBEDDING_BASE_URL=...  # Still works
LLM_EMBEDDING_MODEL=...
LLM_EMBEDDING_API_KEY=...
```

### Switching Providers

Switch at runtime by changing environment variable:

```bash
# Use Ollama
LLM_EMBEDDING_PROVIDER=ollama

# Use OpenAI/GLM
LLM_EMBEDDING_PROVIDER=openai
```

Restart worker for changes to take effect.

## Troubleshooting

### Ollama Not Starting

```bash
# Check if Ollama is running
ps aux | grep ollama

# Check logs
journalctl -u ollama -f  # Linux
brew services info ollama  # macOS

# Restart service
ollama serve
```

### Model Not Loading

```bash
# Verify model exists
ollama list | grep bge-m3

# Re-pull model if needed
ollama pull bge-m3:567m

# Test model directly
ollama run bge-m3:567m "test"
```

### Performance Issues

```bash
# Check batch size (reduce if timeouts)
LLM_EMBEDDING_BATCH_SIZE=32  # Default: 64

# Monitor resource usage
htop  # CPU/RAM
nvidia-smi  # GPU (if applicable)
```

## Implementation Details

### Provider Interface

```python
class BaseEmbeddingProvider(Protocol):
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate single embedding."""
        ...

    async def generate_embeddings_batch(
        self, texts: List[str], batch_size: int
    ) -> List[List[float]]:
        """Generate batch embeddings."""
        ...
```

### API Formats

**OpenAI:**
```json
POST /embeddings
{
  "model": "embedding-3",
  "input": ["text1", "text2"]
}

Response:
{
  "data": [
    {"embedding": [0.1, 0.2, ...]},
    {"embedding": [0.3, 0.4, ...]}
  ]
}
```

**Ollama:**
```json
POST /api/embed
{
  "model": "bge-m3:567m",
  "input": ["text1", "text2"]
}

Response:
{
  "embeddings": [
    [0.1, 0.2, ...],
    [0.3, 0.4, ...]
  ]
}
```

## Future Enhancements

- [ ] Add HuggingFace provider
- [ ] Add local transformers provider
- [ ] Support custom models
- [ ] Add embedding caching
- [ ] Add health check endpoint
- [ ] Add provider metrics dashboard
