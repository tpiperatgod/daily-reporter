"""Provider comparison test - OpenAI vs Ollama embedding providers."""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.embedding.openai_provider import OpenAIEmbeddingProvider
from app.services.embedding.ollama_provider import OllamaEmbeddingProvider
from app.core.logging import get_logger

logger = get_logger(__name__)


async def main():
    """Compare OpenAI and Ollama embedding providers."""
    print("=" * 80)
    print("Embedding Provider Comparison: OpenAI vs Ollama")
    print("=" * 80)

    # Test data
    test_texts = [
        "Breaking: Major AI breakthrough announced today",
        "Tech stocks surge on positive earnings reports",
        "New study reveals surprising health benefits",
        "Climate summit reaches historic agreement",
        "SpaceX launches another batch of satellites"
    ]

    print(f"\nTest dataset: {len(test_texts)} texts")
    print()

    # Test Ollama provider
    print("=" * 80)
    print("1. Testing Ollama Provider (Local)")
    print("=" * 80)

    ollama_provider = OllamaEmbeddingProvider(
        base_url=os.getenv("OLLAMA_EMBEDDING_BASE_URL", "http://localhost:11434"),
        model=os.getenv("OLLAMA_EMBEDDING_MODEL", "bge-m3:567m"),
        batch_size=64
    )

    try:
        import time
        start_time = time.time()

        ollama_embeddings = await ollama_provider.generate_embeddings_batch(
            test_texts, batch_size=64
        )

        ollama_duration = time.time() - start_time

        print(f"\n✅ Ollama Results:")
        print(f"  Total embeddings: {len(ollama_embeddings)}")
        print(f"  Dimension: {len(ollama_embeddings[0])}")
        print(f"  Time taken: {ollama_duration:.2f}s")
        print(f"  Average: {ollama_duration/len(test_texts):.3f}s per embedding")

        ollama_success = True

    except Exception as e:
        print(f"\n❌ Ollama test failed: {e}")
        ollama_success = False
        ollama_embeddings = None
        ollama_duration = None

    finally:
        await ollama_provider.close()

    # Test OpenAI provider (if configured)
    print("\n" + "=" * 80)
    print("2. Testing OpenAI Provider (Remote)")
    print("=" * 80)

    openai_base_url = (
        os.getenv("OPENAI_EMBEDDING_BASE_URL") or
        os.getenv("LLM_EMBEDDING_BASE_URL")
    )
    openai_model = (
        os.getenv("OPENAI_EMBEDDING_MODEL") or
        os.getenv("LLM_EMBEDDING_MODEL")
    )
    openai_api_key = (
        os.getenv("OPENAI_EMBEDDING_API_KEY") or
        os.getenv("LLM_EMBEDDING_API_KEY")
    )

    if not all([openai_base_url, openai_model, openai_api_key]):
        print("\n⚠️  OpenAI provider not configured (skipping)")
        print("   Set OPENAI_EMBEDDING_BASE_URL, OPENAI_EMBEDDING_MODEL, and OPENAI_EMBEDDING_API_KEY")
        openai_success = False
        openai_embeddings = None
        openai_duration = None
    else:
        openai_provider = OpenAIEmbeddingProvider(
            base_url=openai_base_url,
            model=openai_model,
            api_key=openai_api_key,
            batch_size=64
        )

        try:
            start_time = time.time()

            openai_embeddings = await openai_provider.generate_embeddings_batch(
                test_texts, batch_size=64
            )

            openai_duration = time.time() - start_time

            print(f"\n✅ OpenAI Results:")
            print(f"  Total embeddings: {len(openai_embeddings)}")
            print(f"  Dimension: {len(openai_embeddings[0])}")
            print(f"  Time taken: {openai_duration:.2f}s")
            print(f"  Average: {openai_duration/len(test_texts):.3f}s per embedding")

            openai_success = True

        except Exception as e:
            print(f"\n❌ OpenAI test failed: {e}")
            openai_success = False
            openai_embeddings = None
            openai_duration = None

        finally:
            await openai_provider.close()

    # Comparison
    print("\n" + "=" * 80)
    print("3. Comparison Summary")
    print("=" * 80)

    if ollama_success and openai_success:
        print(f"\n📊 Performance Comparison:")
        print(f"  Ollama (local):  {ollama_duration:.2f}s ({ollama_duration/len(test_texts):.3f}s per item)")
        print(f"  OpenAI (remote): {openai_duration:.2f}s ({openai_duration/len(test_texts):.3f}s per item)")

        if ollama_duration < openai_duration:
            speedup = openai_duration / ollama_duration
            print(f"\n  🚀 Ollama is {speedup:.1f}x faster!")
        else:
            speedup = ollama_duration / openai_duration
            print(f"\n  🚀 OpenAI is {speedup:.1f}x faster!")

        print(f"\n📐 Embedding Dimensions:")
        print(f"  Ollama:  {len(ollama_embeddings[0])}")
        print(f"  OpenAI:  {len(openai_embeddings[0])}")

        print(f"\n💰 Cost Considerations:")
        print(f"  Ollama:  Free (local)")
        print(f"  OpenAI:  API costs apply")

        print(f"\n🔒 Privacy:")
        print(f"  Ollama:  Data stays local")
        print(f"  OpenAI:  Data sent to remote API")

    elif ollama_success:
        print(f"\n✅ Ollama provider working")
        print(f"⚠️  OpenAI provider not tested (not configured)")

    elif openai_success:
        print(f"\n✅ OpenAI provider working")
        print(f"⚠️  Ollama provider not working")

    else:
        print(f"\n❌ Both providers failed")
        return 1

    print("\n" + "=" * 80)
    print("Recommendation:")
    print("=" * 80)

    if ollama_success:
        print("\n🎯 Use Ollama for:")
        print("  - Development and testing")
        print("  - Privacy-sensitive data")
        print("  - High-volume processing (no API costs)")
        print("  - Offline/air-gapped environments")

    if openai_success:
        print("\n🎯 Use OpenAI-compatible APIs for:")
        print("  - Production with specific model requirements")
        print("  - Cloud deployment without local GPU")
        print("  - When using existing API subscriptions")

    print("\n" + "=" * 80)

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
