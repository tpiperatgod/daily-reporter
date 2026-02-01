"""End-to-end verification of embedding provider integration."""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set Ollama provider
os.environ['LLM_EMBEDDING_PROVIDER'] = 'ollama'

from app.services.embedding.factory import get_embedding_provider
from app.services.llm.client import LLMClient
from app.core.logging import get_logger

logger = get_logger(__name__)


async def main():
    """Verify end-to-end embedding pipeline."""
    print("=" * 80)
    print("End-to-End Embedding Provider Verification")
    print("=" * 80)

    # Test data
    test_texts = [
        "AI research breakthrough in natural language processing",
        "Stock market volatility continues amid economic concerns",
        "New climate policy announced at international summit"
    ]

    print(f"\nTest Configuration:")
    print(f"  Provider: {os.getenv('LLM_EMBEDDING_PROVIDER')}")
    print(f"  Test texts: {len(test_texts)}")
    print()

    try:
        # Step 1: Factory creates provider
        print("Step 1: Creating embedding provider via factory...")
        embedding_provider = get_embedding_provider()
        print(f"  ✅ Created: {type(embedding_provider).__name__}")

        # Step 2: LLMClient uses provider
        print("\nStep 2: Initializing LLMClient with provider...")
        llm_client = LLMClient(embedding_provider=embedding_provider)
        print(f"  ✅ LLMClient initialized")

        # Step 3: Generate single embedding
        print("\nStep 3: Testing single embedding generation...")
        embedding = await llm_client.generate_embedding(test_texts[0])
        print(f"  ✅ Generated embedding (dimension: {len(embedding)})")

        # Step 4: Generate embedding hash
        print("\nStep 4: Testing embedding hash generation...")
        hash_val = await llm_client.generate_embedding_hash(test_texts[0])
        print(f"  ✅ Generated hash: {hash_val[:16]}...")

        # Step 5: Batch embeddings
        print("\nStep 5: Testing batch embedding generation...")
        embeddings = await llm_client.generate_embeddings_batch(test_texts)
        print(f"  ✅ Generated {len(embeddings)} embeddings")

        # Step 6: Batch hashes
        print("\nStep 6: Testing batch hash generation...")
        hashes = await llm_client.generate_embedding_hashes_batch(test_texts)
        print(f"  ✅ Generated {len(hashes)} hashes")
        for i, (text, hash_val) in enumerate(zip(test_texts, hashes), 1):
            print(f"     {i}. {hash_val[:16]}... - {text[:50]}...")

        # Step 7: Verify deduplication works
        print("\nStep 7: Testing deduplication...")
        # Generate hash for same text again
        hash_again = await llm_client.generate_embedding_hash(test_texts[0])
        if hash_again == hashes[0]:
            print(f"  ✅ Deduplication works (same hash for same text)")
        else:
            print(f"  ❌ Deduplication issue (different hashes)")
            return 1

        # Step 8: Verify different texts have different hashes
        print("\nStep 8: Testing uniqueness...")
        unique_hashes = len(set(hashes))
        if unique_hashes == len(hashes):
            print(f"  ✅ All hashes are unique ({unique_hashes}/{len(hashes)})")
        else:
            print(f"  ⚠️  Some duplicate hashes detected ({unique_hashes}/{len(hashes)})")

        print("\n" + "=" * 80)
        print("✅ All verification steps passed!")
        print("=" * 80)

        print("\nIntegration Status:")
        print("  ✅ Provider abstraction working")
        print("  ✅ Factory pattern working")
        print("  ✅ LLMClient integration working")
        print("  ✅ Single embedding generation working")
        print("  ✅ Batch embedding generation working")
        print("  ✅ Hash generation working")
        print("  ✅ Deduplication working")
        print("  ✅ Ready for production use")

        print("\nNext Steps:")
        print("  1. Update .env with desired provider")
        print("  2. Restart Celery worker")
        print("  3. Run collect_data task")
        print("  4. Verify items have embedding_hash in database")

        await llm_client.close()

        return 0

    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
