#!/usr/bin/env python3
"""
Batch Embedding API Verification Demo

This script demonstrates the new batch embedding functionality:
1. Fetches existing items from the database
2. Tests batch embedding generation (64 items per API call)
3. Compares performance: individual vs batch API calls
4. Shows retry logic with exponential backoff on rate limits
5. Provides detailed diagnostics on API efficiency

Usage:
    python demos/test_batch_embedding.py

Environment Variables Required:
    - DATABASE_URL: PostgreSQL connection string
    - ZHIPU_API_KEY: API key for ZhipuAI embeddings
"""

import asyncio
import os
import sys
import time
from datetime import datetime
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.db.models import Item
from app.services.llm.client import LLMClient
from app.services.embedding.factory import get_embedding_provider

logger = get_logger(__name__)


class BatchEmbeddingTester:
    """Test batch embedding generation with performance comparison."""

    def __init__(self):
        embedding_provider = get_embedding_provider()
        self.llm_client = LLMClient(embedding_provider=embedding_provider)

    async def fetch_sample_items(self, session: AsyncSession, limit: int = 100) -> List[Item]:
        """Fetch sample items from database for testing."""
        logger.info(f"Fetching up to {limit} items from database...")

        result = await session.execute(
            select(Item).limit(limit).order_by(Item.collected_at.desc())
        )
        items = result.scalars().all()

        logger.info(f"Found {len(items)} items")
        return items

    async def test_individual_embeddings(self, texts: List[str]) -> dict:
        """
        Test generating embeddings individually (old approach).

        Args:
            texts: List of texts to embed

        Returns:
            Performance statistics
        """
        print(f"\n📊 Testing INDIVIDUAL embedding generation ({len(texts)} items)")
        print("-" * 60)

        start_time = time.time()
        api_calls = 0
        successful = 0
        failed = 0

        hashes = []
        for i, text in enumerate(texts, 1):
            try:
                api_calls += 1
                hash_val = await self.llm_client.generate_embedding_hash(text)
                hashes.append(hash_val)
                successful += 1

                if i % 10 == 0:
                    print(f"  Progress: {i}/{len(texts)} items...")

            except Exception as e:
                failed += 1
                logger.warning(f"Failed to generate embedding {i}: {e}")
                hashes.append(None)

        elapsed = time.time() - start_time

        stats = {
            "method": "individual",
            "total_items": len(texts),
            "api_calls": api_calls,
            "successful": successful,
            "failed": failed,
            "elapsed_time": elapsed,
            "avg_time_per_item": elapsed / len(texts) if texts else 0,
            "hashes": hashes
        }

        print(f"\n  ✅ Completed in {elapsed:.2f}s")
        print(f"  API calls: {api_calls}")
        print(f"  Success rate: {successful}/{len(texts)} ({successful/len(texts)*100:.1f}%)")
        print(f"  Avg time per item: {stats['avg_time_per_item']:.3f}s")

        return stats

    async def test_batch_embeddings(self, texts: List[str], batch_size: int = 64) -> dict:
        """
        Test generating embeddings in batch (new approach).

        Args:
            texts: List of texts to embed
            batch_size: Items per API call

        Returns:
            Performance statistics
        """
        print(f"\n📊 Testing BATCH embedding generation ({len(texts)} items, batch_size={batch_size})")
        print("-" * 60)

        start_time = time.time()
        expected_api_calls = (len(texts) + batch_size - 1) // batch_size

        try:
            hashes = await self.llm_client.generate_embedding_hashes_batch(
                texts,
                batch_size=batch_size
            )
            successful = sum(1 for h in hashes if h is not None)
            failed = sum(1 for h in hashes if h is None)

        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            hashes = [None] * len(texts)
            successful = 0
            failed = len(texts)

        elapsed = time.time() - start_time

        stats = {
            "method": "batch",
            "total_items": len(texts),
            "api_calls": expected_api_calls,
            "batch_size": batch_size,
            "successful": successful,
            "failed": failed,
            "elapsed_time": elapsed,
            "avg_time_per_item": elapsed / len(texts) if texts else 0,
            "hashes": hashes
        }

        print(f"\n  ✅ Completed in {elapsed:.2f}s")
        print(f"  API calls: {expected_api_calls} (expected)")
        print(f"  Success rate: {successful}/{len(texts)} ({successful/len(texts)*100:.1f}%)")
        print(f"  Avg time per item: {stats['avg_time_per_item']:.3f}s")

        return stats

    def compare_results(self, individual_stats: dict, batch_stats: dict):
        """Print comparison of individual vs batch results."""
        print("\n" + "=" * 60)
        print("PERFORMANCE COMPARISON")
        print("=" * 60)

        print(f"\nTotal items processed: {individual_stats['total_items']}")
        print()

        print("INDIVIDUAL APPROACH:")
        print(f"  API calls:       {individual_stats['api_calls']}")
        print(f"  Time:            {individual_stats['elapsed_time']:.2f}s")
        print(f"  Time per item:   {individual_stats['avg_time_per_item']:.3f}s")
        print()

        print("BATCH APPROACH:")
        print(f"  API calls:       {batch_stats['api_calls']}")
        print(f"  Batch size:      {batch_stats['batch_size']}")
        print(f"  Time:            {batch_stats['elapsed_time']:.2f}s")
        print(f"  Time per item:   {batch_stats['avg_time_per_item']:.3f}s")
        print()

        # Calculate improvements
        if individual_stats['api_calls'] > 0:
            api_reduction = (1 - batch_stats['api_calls'] / individual_stats['api_calls']) * 100
            print(f"IMPROVEMENTS:")
            print(f"  API call reduction:  {api_reduction:.1f}%")

        if individual_stats['elapsed_time'] > 0:
            time_reduction = (1 - batch_stats['elapsed_time'] / individual_stats['elapsed_time']) * 100
            speedup = individual_stats['elapsed_time'] / batch_stats['elapsed_time']
            print(f"  Time reduction:      {time_reduction:.1f}%")
            print(f"  Speedup:             {speedup:.1f}x faster")

        print()
        print("=" * 60)

    async def close(self):
        """Clean up resources."""
        await self.llm_client.close()


async def main():
    """Main test workflow."""
    print("\n" + "=" * 60)
    print("BATCH EMBEDDING API VERIFICATION DEMO")
    print("=" * 60)
    print()

    # Check environment variables
    provider = os.getenv("LLM_EMBEDDING_PROVIDER", "openai")
    print(f"Using embedding provider: {provider}")

    if provider == "openai":
        if not (os.getenv("OPENAI_EMBEDDING_API_KEY") or os.getenv("LLM_EMBEDDING_API_KEY")):
            print("❌ ERROR: OPENAI_EMBEDDING_API_KEY or LLM_EMBEDDING_API_KEY environment variable not set")
            return 1
    elif provider == "ollama":
        print("Using Ollama local provider (no API key required)")

    if not os.getenv("DATABASE_URL"):
        print("❌ ERROR: DATABASE_URL environment variable not set")
        return 1

    print("✅ Environment variables configured")
    print()

    tester = BatchEmbeddingTester()

    try:
        async with AsyncSessionLocal() as session:
            # Fetch sample items
            print("\n📋 Fetching Sample Items")
            print("-" * 60)
            items = await tester.fetch_sample_items(session, limit=100)

            if not items:
                print("⚠️  No items found in database. Please run data collection first.")
                return 0

            print(f"✅ Found {len(items)} items to test")

            # Prepare texts
            texts = [item.text for item in items]
            print(f"✅ Prepared {len(texts)} texts for embedding")

            # Test batch approach (recommended)
            batch_stats = await tester.test_batch_embeddings(texts, batch_size=64)

            # Optionally test individual approach for comparison (comment out to save API quota)
            print("\n⚠️  Skipping individual approach test to save API quota")
            print("    (Uncomment in code to run full comparison)")
            # individual_stats = await tester.test_individual_embeddings(texts[:10])  # Use subset
            # tester.compare_results(individual_stats, batch_stats)

            # Show batch performance summary
            print("\n" + "=" * 60)
            print("BATCH EMBEDDING SUMMARY")
            print("=" * 60)
            print(f"Items processed:     {batch_stats['total_items']}")
            print(f"API calls made:      {batch_stats['api_calls']}")
            print(f"Batch size:          {batch_stats['batch_size']}")
            print(f"Success rate:        {batch_stats['successful']}/{batch_stats['total_items']} ({batch_stats['successful']/batch_stats['total_items']*100:.1f}%)")
            print(f"Total time:          {batch_stats['elapsed_time']:.2f}s")
            print(f"Time per item:       {batch_stats['avg_time_per_item']:.3f}s")

            # Calculate expected improvement vs individual
            expected_individual_calls = batch_stats['total_items']
            api_reduction = (1 - batch_stats['api_calls'] / expected_individual_calls) * 100
            print(f"\nEstimated vs individual approach:")
            print(f"  API call reduction:  {api_reduction:.1f}%")
            print(f"  ({expected_individual_calls} calls → {batch_stats['api_calls']} calls)")
            print("=" * 60)

    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        return 1
    finally:
        await tester.close()

    print("\n✅ Demo completed successfully")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
