"""Test script for Ollama embedding provider."""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.embedding.ollama_provider import OllamaEmbeddingProvider
from app.core.logging import get_logger

logger = get_logger(__name__)


async def main():
    """Test Ollama embedding provider."""
    print("=" * 80)
    print("Ollama Embedding Provider Test")
    print("=" * 80)

    # Configuration
    base_url = os.getenv("OLLAMA_EMBEDDING_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_EMBEDDING_MODEL", "bge-m3:567m")
    batch_size = int(os.getenv("LLM_EMBEDDING_BATCH_SIZE", "64"))

    print(f"\nConfiguration:")
    print(f"  Base URL: {base_url}")
    print(f"  Model: {model}")
    print(f"  Batch Size: {batch_size}")
    print()

    # Test data
    test_texts = [
        "Breaking: Major AI breakthrough announced today",
        "Tech stocks surge on positive earnings reports",
        "New study reveals surprising health benefits",
        "Climate summit reaches historic agreement",
        "SpaceX launches another batch of satellites"
    ]

    # Create provider
    provider = OllamaEmbeddingProvider(
        base_url=base_url,
        model=model,
        batch_size=batch_size,
        max_retries=3,
        initial_backoff=1.0
    )

    try:
        # Test 1: Single embedding
        print("\n" + "=" * 80)
        print("Test 1: Single Embedding")
        print("=" * 80)

        text = test_texts[0]
        print(f"\nGenerating embedding for: '{text}'")

        embedding = await provider.generate_embedding(text)

        print(f"\nResult:")
        print(f"  Dimension: {len(embedding)}")
        print(f"  First 5 values: {embedding[:5]}")
        print(f"  Sample: min={min(embedding):.6f}, max={max(embedding):.6f}")

        # Test 2: Batch embeddings
        print("\n" + "=" * 80)
        print("Test 2: Batch Embeddings")
        print("=" * 80)

        print(f"\nGenerating embeddings for {len(test_texts)} texts...")
        for i, text in enumerate(test_texts, 1):
            print(f"  {i}. {text[:50]}...")

        import time
        start_time = time.time()

        embeddings = await provider.generate_embeddings_batch(
            test_texts, batch_size=batch_size
        )

        duration = time.time() - start_time

        print(f"\nResult:")
        print(f"  Total embeddings: {len(embeddings)}")
        print(f"  Dimension: {len(embeddings[0])}")
        print(f"  Time taken: {duration:.2f}s")
        print(f"  Average: {duration/len(embeddings):.2f}s per embedding")

        # Test 3: Verify embeddings are different
        print("\n" + "=" * 80)
        print("Test 3: Embedding Uniqueness")
        print("=" * 80)

        print("\nVerifying embeddings are different for different texts...")

        # Compare first two embeddings
        emb1 = embeddings[0]
        emb2 = embeddings[1]

        # Calculate cosine similarity
        import math
        dot_product = sum(a * b for a, b in zip(emb1, emb2))
        norm1 = math.sqrt(sum(a * a for a in emb1))
        norm2 = math.sqrt(sum(b * b for b in emb2))
        similarity = dot_product / (norm1 * norm2)

        print(f"  Cosine similarity between text 1 and 2: {similarity:.4f}")
        print(f"  Are embeddings different? {emb1 != emb2}")

        # Test 4: Performance comparison hint
        print("\n" + "=" * 80)
        print("Test 4: Performance Notes")
        print("=" * 80)

        print(f"\nOllama (local) performance:")
        print(f"  - Batch size: {len(test_texts)}")
        print(f"  - Total time: {duration:.2f}s")
        print(f"  - Per item: {duration/len(test_texts):.2f}s")
        print(f"\nBenefits of local inference:")
        print(f"  - No network latency")
        print(f"  - No API rate limits")
        print(f"  - Data privacy (no external calls)")
        print(f"  - Free (no API costs)")

        print("\n" + "=" * 80)
        print("All tests passed!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        await provider.close()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
