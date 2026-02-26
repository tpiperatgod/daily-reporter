from typing import List
from datetime import datetime, timedelta
import random
from app.services.provider.base import RawItem


class MockAdapter:
    """
    Mock provider for development and testing.

    Returns realistic hardcoded tweets for various topics without
    requiring external API calls.
    """

    # Mock data templates for different topics
    MOCK_TWEETS = {
        "AI": [
            {
                "author": "OpenAI",
                "text": "Excited to announce GPT-5 is now in development! We're pushing the boundaries of what's possible with AI. #AI #MachineLearning",
                "metrics": {
                    "likes": 5420,
                    "retweets": 1203,
                    "replies": 342,
                    "views": 120000,
                },
            },
            {
                "author": "Andrew Ng",
                "text": "Just finished teaching my new AI course. The future of AI is bright - we're seeing breakthroughs in multimodal learning every day. Here are my top 5 predictions for 2025...",
                "metrics": {
                    "likes": 8934,
                    "retweets": 2341,
                    "replies": 567,
                    "views": 340000,
                },
            },
            {
                "author": "Sam Altman",
                "text": "AGI might be closer than we think. The rate of improvement we're seeing is unprecedented. Stay tuned for some big announcements coming soon.",
                "metrics": {
                    "likes": 15678,
                    "retweets": 4521,
                    "replies": 1203,
                    "views": 560000,
                },
            },
            {
                "author": "Demis Hassabis",
                "text": "DeepMind's AlphaFold 3 is now predicting protein interactions with 97% accuracy. This will revolutionize drug discovery. Nature paper out tomorrow!",
                "metrics": {
                    "likes": 12456,
                    "retweets": 3890,
                    "replies": 892,
                    "views": 450000,
                },
            },
            {
                "author": "Yann LeCun",
                "text": "Self-supervised learning is the key to AGI. I've been saying this for years, and the evidence keeps mounting. Check out our latest paper on JEPA architecture.",
                "metrics": {
                    "likes": 7234,
                    "retweets": 1834,
                    "replies": 445,
                    "views": 210000,
                },
            },
            {
                "author": "Geoffrey Hinton",
                "text": "After decades of research, neural networks have finally come of age. The progress in the last 5 years has been remarkable. But we must also consider the ethical implications carefully.",
                "metrics": {
                    "likes": 9876,
                    "retweets": 2156,
                    "replies": 678,
                    "views": 289000,
                },
            },
            {
                "author": "Fei-Fei Li",
                "text": "Computer vision has transformed from hand-crafted features to deep learning. Now we're entering the era of visual reasoning - AI that truly understands images like humans do.",
                "metrics": {
                    "likes": 6543,
                    "retweets": 1543,
                    "replies": 389,
                    "views": 178000,
                },
            },
            {
                "author": "AI Research Weekly",
                "text": "📊 This Week in AI:\n• GPT-4 achieves human-level performance on bar exam\n• New breakthrough in efficient transformer architectures\n• EU finalizes AI Act regulations\n• Google announces Gemini 2.0\n\nRead our full analysis 👇",
                "metrics": {
                    "likes": 3456,
                    "retweets": 987,
                    "replies": 234,
                    "views": 89000,
                },
            },
        ],
        "crypto": [
            {
                "author": "Vitalik Buterin",
                "text": "Ethereum just successfully implemented another major upgrade. Gas fees are down 40% and transaction speed has improved significantly. The future of DeFi is looking bright! 🚀 #Ethereum #Crypto",
                "metrics": {
                    "likes": 12345,
                    "retweets": 3456,
                    "replies": 890,
                    "views": 670000,
                },
            },
            {
                "author": "Elon Musk",
                "text": "Dogecoin to the moon! 🌕 Just had a great meeting about potential integrations. The power of decentralized currency is real.",
                "metrics": {
                    "likes": 45678,
                    "retweets": 12345,
                    "replies": 3456,
                    "views": 2300000,
                },
            },
            {
                "author": "CoinDesk",
                "text": "BREAKING: Bitcoin surges past $75,000 as institutional adoption accelerates. Major banks are now offering crypto services to retail customers. Here's what you need to know... 📈",
                "metrics": {
                    "likes": 8765,
                    "retweets": 2345,
                    "replies": 678,
                    "views": 234000,
                },
            },
            {
                "author": " CZ",
                "text": "Market volatility is normal. Don't panic sell. DYOR and HODL. The blockchain revolution is just getting started. 🔐 #Bitcoin #HODL",
                "metrics": {
                    "likes": 5678,
                    "retweets": 1543,
                    "replies": 423,
                    "views": 145000,
                },
            },
        ],
        "tech": [
            {
                "author": "Sundar Pichai",
                "text": "Google I/O is next week! We have some exciting announcements about AI, Android 15, and cloud computing. The future of technology is being built right now. 👨‍💻 #GoogleIO #Tech",
                "metrics": {
                    "likes": 7890,
                    "retweets": 2103,
                    "replies": 567,
                    "views": 198000,
                },
            },
            {
                "author": "Satya Nadella",
                "text": "Microsoft Azure is now the fastest growing cloud platform. Our AI integrations are helping businesses transform at scale. Great quarter ahead! ☁️ #Azure #CloudComputing",
                "metrics": {
                    "likes": 5432,
                    "retweets": 1432,
                    "replies": 345,
                    "views": 123000,
                },
            },
            {
                "author": "TechCrunch",
                "text": "The startup funding landscape is shifting. AI startups are raising record rounds while traditional SaaS faces scrutiny. Our full report on Q1 2025 trends is out now. 📊",
                "metrics": {
                    "likes": 3456,
                    "retweets": 890,
                    "replies": 234,
                    "views": 89000,
                },
            },
        ],
        "default": [
            {
                "author": "News Daily",
                "text": "Breaking: Major developments in the tech industry today as companies announce new initiatives and partnerships. Stay tuned for more updates. #News #Tech",
                "metrics": {
                    "likes": 1234,
                    "retweets": 345,
                    "replies": 89,
                    "views": 45000,
                },
            },
            {
                "author": "Industry Watch",
                "text": "Analysis: What the latest market trends mean for consumers and businesses. Our experts weigh in on the implications of recent developments.",
                "metrics": {
                    "likes": 876,
                    "retweets": 234,
                    "replies": 56,
                    "views": 32000,
                },
            },
            {
                "author": "Tech Insider",
                "text": "Hot Take: The next big thing in technology isn't what you expect. Our analysis suggests a major shift in consumer behavior coming in 2025.",
                "metrics": {
                    "likes": 2345,
                    "retweets": 567,
                    "replies": 123,
                    "views": 67000,
                },
            },
        ],
    }

    def __init__(self):
        """Initialize the mock adapter."""
        self.tweet_counter = 1000  # Start tweet IDs from 1000

    async def fetch(self, query: str, start_date: datetime, end_date: datetime, max_items: int = 100) -> List[RawItem]:
        """
        Fetch mock tweets based on the query.

        Args:
            query: Search query (used to select topic)
            start_date: Start of time window
            end_date: End of time window
            max_items: Maximum items to return

        Returns:
            List of RawItem objects
        """
        # Select appropriate mock data based on query
        query_lower = query.lower()
        mock_data = []

        if "ai" in query_lower or "machine learning" in query_lower or "gpt" in query_lower:
            mock_data = self.MOCK_TWEETS.get("AI", self.MOCK_TWEETS["default"])
        elif "crypto" in query_lower or "bitcoin" in query_lower or "ethereum" in query_lower:
            mock_data = self.MOCK_TWEETS.get("crypto", self.MOCK_TWEETS["default"])
        elif "tech" in query_lower or "startup" in query_lower or "software" in query_lower:
            mock_data = self.MOCK_TWEETS.get("tech", self.MOCK_TWEETS["default"])
        else:
            mock_data = self.MOCK_TWEETS["default"]

        # Generate items with variations
        items = []
        num_items = min(max_items, len(mock_data) * 3)  # Generate up to 3x the base data

        for i in range(num_items):
            base_tweet = mock_data[i % len(mock_data)]

            # Vary timestamps within the window
            time_diff = end_date - start_date
            random_offset = timedelta(
                days=random.randint(0, time_diff.days),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )
            created_at = start_date + random_offset

            # Create item
            item = RawItem(
                source_id=f"mock_tweet_{self.tweet_counter + i}",
                author=base_tweet["author"],
                text=base_tweet["text"],
                url=f"https://twitter.com/{base_tweet['author'].lower().replace(' ', '')}/status/{self.tweet_counter + i}",
                created_at=created_at,
                media_urls=[],
                metrics=base_tweet["metrics"],
            )
            items.append(item)

        return items
