from typing import List, Optional
from datetime import datetime, timedelta
import random
import logging
from app.services.provider.base import BaseProvider, RawItem

logger = logging.getLogger(__name__)


class MockAdapter:
    """
    Mock provider for development and testing.

    Returns realistic hardcoded tweets for various topics without
    requiring external API calls.
    """

    # Mock data templates - flat list with IDs and topic tags
    MOCK_TWEETS = [
        # AI/ML tweets (IDs 1000-1019)
        {
            "id": 1000,
            "author": "OpenAI",
            "text": "Excited to announce GPT-5 is now in development! We're pushing the boundaries of what's possible with AI. #AI #MachineLearning",
            "metrics": {"likes": 5420, "retweets": 1203, "replies": 342, "quotes": 89, "views": 120000},
            "media_urls": [],
            "topics": ["ai", "machine learning", "gpt"]
        },
        {
            "id": 1001,
            "author": "Andrew Ng",
            "text": "Just finished teaching my new AI course. The future of AI is bright - we're seeing breakthroughs in multimodal learning every day.",
            "metrics": {"likes": 8934, "retweets": 2341, "replies": 567, "quotes": 145, "views": 340000},
            "media_urls": ["https://pbs.twimg.com/media/ai_course_preview.jpg"],
            "topics": ["ai", "education"]
        },
        {
            "id": 1002,
            "author": "Sam Altman",
            "text": "AGI might be closer than we think. The rate of improvement we're seeing is unprecedented. Stay tuned for some big announcements coming soon.",
            "metrics": {"likes": 15678, "retweets": 4521, "replies": 1203, "quotes": 267, "views": 560000},
            "media_urls": [],
            "topics": ["ai", "agi"]
        },
        {
            "id": 1003,
            "author": "Demis Hassabis",
            "text": "DeepMind's AlphaFold 3 is now predicting protein interactions with 97% accuracy. This will revolutionize drug discovery. Nature paper out tomorrow!",
            "metrics": {"likes": 12456, "retweets": 3890, "replies": 892, "quotes": 201, "views": 450000},
            "media_urls": ["https://pbs.twimg.com/media/alphafold_visualization.png"],
            "topics": ["ai", "science", "biology"]
        },
        {
            "id": 1004,
            "author": "Yann LeCun",
            "text": "Self-supervised learning is the key to AGI. I've been saying this for years, and the evidence keeps mounting. Check out our latest paper on JEPA architecture.",
            "metrics": {"likes": 7234, "retweets": 1834, "replies": 445, "quotes": 112, "views": 210000},
            "media_urls": [],
            "topics": ["ai", "machine learning"]
        },
        {
            "id": 1005,
            "author": "Geoffrey Hinton",
            "text": "After decades of research, neural networks have finally come of age. The progress in the last 5 years has been remarkable. But we must also consider the ethical implications carefully.",
            "metrics": {"likes": 9876, "retweets": 2156, "replies": 678, "quotes": 156, "views": 289000},
            "media_urls": [],
            "topics": ["ai", "ethics"]
        },
        {
            "id": 1006,
            "author": "Fei-Fei Li",
            "text": "Computer vision has transformed from hand-crafted features to deep learning. Now we're entering the era of visual reasoning - AI that truly understands images like humans do.",
            "metrics": {"likes": 6543, "retweets": 1543, "replies": 389, "quotes": 98, "views": 178000},
            "media_urls": [],
            "topics": ["ai", "computer vision"]
        },
        {
            "id": 1007,
            "author": "Andrej Karpathy",
            "text": "Training large language models is getting more efficient. Our latest findings show we can reduce compute by 30% with better data curation. Details in the blog post.",
            "metrics": {"likes": 11234, "retweets": 3012, "replies": 734, "quotes": 189, "views": 387000},
            "media_urls": ["https://pbs.twimg.com/media/training_efficiency_chart.jpg"],
            "topics": ["ai", "machine learning"]
        },
        {
            "id": 1008,
            "author": "AI Research Weekly",
            "text": "📊 This Week in AI:\n• GPT-4 achieves human-level performance on bar exam\n• New breakthrough in efficient transformer architectures\n• EU finalizes AI Act regulations\n• Google announces Gemini 2.0\n\nRead our full analysis 👇",
            "metrics": {"likes": 3456, "retweets": 987, "replies": 234, "quotes": 67, "views": 89000},
            "media_urls": [],
            "topics": ["ai", "news"]
        },
        {
            "id": 1009,
            "author": "DeepMind",
            "text": "Our new reinforcement learning algorithm achieves state-of-the-art results on 57 Atari games. The agent learns to play from pixels in just 2 hours. Paper: arxiv.org/...",
            "metrics": {"likes": 8765, "retweets": 2234, "replies": 556, "quotes": 134, "views": 245000},
            "media_urls": [],
            "topics": ["ai", "reinforcement learning"]
        },
        {
            "id": 1010,
            "author": "Stability AI",
            "text": "Stable Diffusion 4.0 is here! Text-to-image generation has never been this good. Try it now and see the future of creative AI.",
            "metrics": {"likes": 19876, "retweets": 5432, "replies": 1456, "quotes": 389, "views": 678000},
            "media_urls": ["https://pbs.twimg.com/media/sd4_sample1.jpg", "https://pbs.twimg.com/media/sd4_sample2.jpg"],
            "topics": ["ai", "generative ai", "art"]
        },
        {
            "id": 1011,
            "author": "Anthropic",
            "text": "Claude 3 Opus is now available via API. Constitutional AI principles ensure helpful, harmless, and honest responses. Check out our benchmark results!",
            "metrics": {"likes": 13456, "retweets": 3789, "replies": 987, "quotes": 234, "views": 456000},
            "media_urls": [],
            "topics": ["ai", "llm"]
        },
        {
            "id": 1012,
            "author": "Hugging Face",
            "text": "We just hit 500,000 models on the Hub! 🤗 The open-source AI community is thriving. Thank you to everyone contributing!",
            "metrics": {"likes": 22345, "retweets": 6789, "replies": 1234, "quotes": 456, "views": 789000},
            "media_urls": [],
            "topics": ["ai", "open source"]
        },
        {
            "id": 1013,
            "author": "Meta AI",
            "text": "LLaMA 3 is now open source! 70B parameters, multilingual support, and competitive with proprietary models. Download weights at meta.ai/llama",
            "metrics": {"likes": 28765, "retweets": 8234, "replies": 1876, "quotes": 567, "views": 923000},
            "media_urls": [],
            "topics": ["ai", "open source", "llm"]
        },
        {
            "id": 1014,
            "author": "Mistral AI",
            "text": "Mixtral 8x7B outperforms GPT-3.5 on most benchmarks. Sparse mixture of experts is the future of efficient LLMs. Apache 2.0 license!",
            "metrics": {"likes": 16543, "retweets": 4321, "replies": 1087, "quotes": 298, "views": 567000},
            "media_urls": [],
            "topics": ["ai", "llm", "open source"]
        },
        {
            "id": 1015,
            "author": "Google AI",
            "text": "Gemini Ultra achieves 90% on MMLU benchmark, the first model to surpass expert-level performance. Multimodal capabilities are game-changing.",
            "metrics": {"likes": 18234, "retweets": 5012, "replies": 1345, "quotes": 387, "views": 645000},
            "media_urls": ["https://pbs.twimg.com/media/gemini_benchmark_chart.png"],
            "topics": ["ai", "google", "multimodal"]
        },
        {
            "id": 1016,
            "author": "Cohere",
            "text": "Command R+ is now available for enterprise customers. Best-in-class retrieval augmented generation with 128k context window. Try the demo!",
            "metrics": {"likes": 7890, "retweets": 2103, "replies": 534, "quotes": 145, "views": 234000},
            "media_urls": [],
            "topics": ["ai", "enterprise", "rag"]
        },
        {
            "id": 1017,
            "author": "Runway ML",
            "text": "Gen-3 Alpha: Our most advanced text-to-video model yet. Create photorealistic videos from text prompts in seconds. The creative possibilities are endless! 🎬",
            "metrics": {"likes": 25678, "retweets": 7234, "replies": 1678, "quotes": 489, "views": 876000},
            "media_urls": ["https://pbs.twimg.com/media/gen3_sample_video.mp4"],
            "topics": ["ai", "video generation", "generative ai"]
        },
        {
            "id": 1018,
            "author": "Perplexity AI",
            "text": "We're processing 50M+ searches per month now. AI-powered search is here to stay. Thanks to our amazing community for the support! 🚀",
            "metrics": {"likes": 12876, "retweets": 3456, "replies": 789, "quotes": 198, "views": 456000},
            "media_urls": [],
            "topics": ["ai", "search"]
        },
        {
            "id": 1019,
            "author": "Inflection AI",
            "text": "Pi assistant now has 1M+ daily active users. Personal AI is becoming mainstream. The future of human-AI interaction is conversational.",
            "metrics": {"likes": 9876, "retweets": 2567, "replies": 645, "quotes": 167, "views": 345000},
            "media_urls": [],
            "topics": ["ai", "assistant"]
        },

        # Crypto tweets (IDs 1020-1039)
        {
            "id": 1020,
            "author": "Vitalik Buterin",
            "text": "Ethereum just successfully implemented another major upgrade. Gas fees are down 40% and transaction speed has improved significantly. The future of DeFi is looking bright! 🚀 #Ethereum #Crypto",
            "metrics": {"likes": 12345, "retweets": 3456, "replies": 890, "quotes": 234, "views": 670000},
            "media_urls": [],
            "topics": ["crypto", "ethereum", "defi"]
        },
        {
            "id": 1021,
            "author": "CZ Binance",
            "text": "Market volatility is normal. Don't panic sell. DYOR and HODL. The blockchain revolution is just getting started. 🔐 #Bitcoin #HODL",
            "metrics": {"likes": 5678, "retweets": 1543, "replies": 423, "quotes": 112, "views": 145000},
            "media_urls": [],
            "topics": ["crypto", "bitcoin", "trading"]
        },
        {
            "id": 1022,
            "author": "CoinDesk",
            "text": "BREAKING: Bitcoin surges past $75,000 as institutional adoption accelerates. Major banks are now offering crypto services to retail customers. Here's what you need to know... 📈",
            "metrics": {"likes": 8765, "retweets": 2345, "replies": 678, "quotes": 189, "views": 234000},
            "media_urls": ["https://pbs.twimg.com/media/btc_price_chart.png"],
            "topics": ["crypto", "bitcoin", "news"]
        },
        {
            "id": 1023,
            "author": "Brian Armstrong",
            "text": "Coinbase Q1 earnings beat expectations. Crypto adoption is accelerating faster than we predicted. Excited for what's coming in 2025!",
            "metrics": {"likes": 9234, "retweets": 2678, "replies": 567, "quotes": 145, "views": 287000},
            "media_urls": [],
            "topics": ["crypto", "business", "coinbase"]
        },
        {
            "id": 1024,
            "author": "Michael Saylor",
            "text": "MicroStrategy just purchased another $500M in Bitcoin. We now hold over 200,000 BTC. Bitcoin is the future of corporate treasury management.",
            "metrics": {"likes": 18765, "retweets": 5234, "replies": 1234, "quotes": 345, "views": 567000},
            "media_urls": [],
            "topics": ["crypto", "bitcoin", "business"]
        },
        {
            "id": 1025,
            "author": "Cathie Wood",
            "text": "Our Bitcoin price target for 2030 is $1.5M per coin. The convergence of institutional adoption and scarcity will drive unprecedented growth. #ARKInvest",
            "metrics": {"likes": 15678, "retweets": 4321, "replies": 1876, "quotes": 456, "views": 489000},
            "media_urls": [],
            "topics": ["crypto", "bitcoin", "investment"]
        },
        {
            "id": 1026,
            "author": "Balaji Srinivasan",
            "text": "The Network State is happening. Bitcoin enables sovereign individuals, Ethereum enables sovereign communities. Web3 is the coordination layer for humanity.",
            "metrics": {"likes": 11234, "retweets": 3456, "replies": 789, "quotes": 198, "views": 345000},
            "media_urls": [],
            "topics": ["crypto", "web3", "philosophy"]
        },
        {
            "id": 1027,
            "author": "Uniswap",
            "text": "Uniswap v4 is live! Hooks enable customizable liquidity pools. DEX innovation continues - we've processed $2T in volume since launch. 🦄",
            "metrics": {"likes": 22345, "retweets": 6789, "replies": 1456, "quotes": 389, "views": 678000},
            "media_urls": [],
            "topics": ["crypto", "defi", "ethereum"]
        },
        {
            "id": 1028,
            "author": "Aave",
            "text": "Total value locked in Aave just crossed $15B! DeFi is maturing. Our GHO stablecoin is gaining traction. Thank you to the community!",
            "metrics": {"likes": 13456, "retweets": 3789, "replies": 891, "quotes": 234, "views": 456000},
            "media_urls": [],
            "topics": ["crypto", "defi", "stablecoin"]
        },
        {
            "id": 1029,
            "author": "Solana",
            "text": "Solana is now processing 65,000 TPS with sub-second finality. Firedancer upgrade next month will push us even further. The fastest blockchain keeps getting faster! ⚡",
            "metrics": {"likes": 19876, "retweets": 5432, "replies": 1234, "quotes": 345, "views": 589000},
            "media_urls": [],
            "topics": ["crypto", "solana", "blockchain"]
        },
        {
            "id": 1030,
            "author": "Polygon",
            "text": "zkEVM mainnet is live! Ethereum scaling with zero-knowledge proofs is here. Deploy your dApps and experience 100x lower gas fees.",
            "metrics": {"likes": 16543, "retweets": 4321, "replies": 1087, "quotes": 289, "views": 478000},
            "media_urls": [],
            "topics": ["crypto", "ethereum", "layer2"]
        },
        {
            "id": 1031,
            "author": "Arbitrum",
            "text": "Arbitrum Orbit allows anyone to launch their own Layer 3 chain. Scaling Ethereum is now composable. The rollup roadmap continues! 🌐",
            "metrics": {"likes": 14567, "retweets": 3987, "replies": 945, "quotes": 256, "views": 423000},
            "media_urls": [],
            "topics": ["crypto", "ethereum", "layer2"]
        },
        {
            "id": 1032,
            "author": "Chainlink",
            "text": "Chainlink CCIP is now securing $5B+ in cross-chain value. The internet of contracts is becoming reality. 80+ blockchains connected!",
            "metrics": {"likes": 12876, "retweets": 3456, "replies": 789, "quotes": 198, "views": 389000},
            "media_urls": [],
            "topics": ["crypto", "oracle", "interoperability"]
        },
        {
            "id": 1033,
            "author": "Circle",
            "text": "USDC market cap just hit $50B. Stablecoins are the killer app of crypto. Millions of people worldwide use USDC for payments and remittances daily.",
            "metrics": {"likes": 10234, "retweets": 2876, "replies": 678, "quotes": 167, "views": 312000},
            "media_urls": [],
            "topics": ["crypto", "stablecoin", "payments"]
        },
        {
            "id": 1034,
            "author": "Tether",
            "text": "USDT processes more daily transaction volume than Visa. The world's most used stablecoin continues to grow. $110B market cap and counting! 💵",
            "metrics": {"likes": 8765, "retweets": 2345, "replies": 567, "quotes": 145, "views": 267000},
            "media_urls": [],
            "topics": ["crypto", "stablecoin"]
        },
        {
            "id": 1035,
            "author": "MakerDAO",
            "text": "DAI supply now at $6B. Decentralized stablecoins are essential for DeFi resilience. The Endgame Plan is progressing well!",
            "metrics": {"likes": 9876, "retweets": 2678, "replies": 645, "quotes": 178, "views": 298000},
            "media_urls": [],
            "topics": ["crypto", "defi", "stablecoin"]
        },
        {
            "id": 1036,
            "author": "Lido Finance",
            "text": "Over 9M ETH staked through Lido! Liquid staking is democratizing Ethereum staking. stETH is the most used DeFi primitive.",
            "metrics": {"likes": 15234, "retweets": 4123, "replies": 987, "quotes": 267, "views": 445000},
            "media_urls": [],
            "topics": ["crypto", "ethereum", "staking"]
        },
        {
            "id": 1037,
            "author": "Cosmos",
            "text": "The Inter-Blockchain Communication protocol now connects 100+ sovereign chains. The internet of blockchains vision is materializing! 🌌",
            "metrics": {"likes": 11876, "retweets": 3234, "replies": 756, "quotes": 189, "views": 367000},
            "media_urls": [],
            "topics": ["crypto", "cosmos", "interoperability"]
        },
        {
            "id": 1038,
            "author": "Avalanche",
            "text": "Subnets enable custom blockchain deployments in minutes. Over 500 subnets launched! The most scalable smart contracts platform keeps innovating. 🔺",
            "metrics": {"likes": 13456, "retweets": 3678, "replies": 834, "quotes": 212, "views": 398000},
            "media_urls": [],
            "topics": ["crypto", "avalanche", "blockchain"]
        },
        {
            "id": 1039,
            "author": "Sui Network",
            "text": "Sui achieves 297,000 TPS in testnet! Move programming language + object-centric architecture = next-gen blockchain performance. Mainnet soon! 🌊",
            "metrics": {"likes": 17654, "retweets": 4765, "replies": 1123, "quotes": 298, "views": 512000},
            "media_urls": [],
            "topics": ["crypto", "sui", "blockchain"]
        },

        # Tech/Startup tweets (IDs 1040-1059)
        {
            "id": 1040,
            "author": "Sundar Pichai",
            "text": "Google I/O is next week! We have some exciting announcements about AI, Android 15, and cloud computing. The future of technology is being built right now. 👨‍💻 #GoogleIO #Tech",
            "metrics": {"likes": 7890, "retweets": 2103, "replies": 567, "quotes": 145, "views": 198000},
            "media_urls": [],
            "topics": ["tech", "google", "cloud"]
        },
        {
            "id": 1041,
            "author": "Satya Nadella",
            "text": "Microsoft Azure is now the fastest growing cloud platform. Our AI integrations are helping businesses transform at scale. Great quarter ahead! ☁️ #Azure #CloudComputing",
            "metrics": {"likes": 5432, "retweets": 1432, "replies": 345, "quotes": 89, "views": 123000},
            "media_urls": [],
            "topics": ["tech", "microsoft", "cloud"]
        },
        {
            "id": 1042,
            "author": "TechCrunch",
            "text": "The startup funding landscape is shifting. AI startups are raising record rounds while traditional SaaS faces scrutiny. Our full report on Q1 2025 trends is out now. 📊",
            "metrics": {"likes": 3456, "retweets": 890, "replies": 234, "quotes": 67, "views": 89000},
            "media_urls": ["https://pbs.twimg.com/media/funding_report_q1.pdf"],
            "topics": ["tech", "startup", "funding"]
        },
        {
            "id": 1043,
            "author": "Tim Cook",
            "text": "Apple Vision Pro sales exceeded our expectations. Spatial computing is the future. Wait until you see what we have planned for WWDC! 🍎",
            "metrics": {"likes": 19876, "retweets": 5432, "replies": 1345, "quotes": 367, "views": 678000},
            "media_urls": [],
            "topics": ["tech", "apple", "vr"]
        },
        {
            "id": 1044,
            "author": "Jensen Huang",
            "text": "NVIDIA H100 GPUs are powering the AI revolution. Demand is unprecedented. We're scaling production to meet the needs of the entire industry. 🚀",
            "metrics": {"likes": 22345, "retweets": 6543, "replies": 1567, "quotes": 423, "views": 789000},
            "media_urls": [],
            "topics": ["tech", "hardware", "ai"]
        },
        {
            "id": 1045,
            "author": "Jeff Bezos",
            "text": "Blue Origin successfully completed another crewed flight to space. Reusable rockets are making space accessible. The future is closer than you think! 🚀",
            "metrics": {"likes": 28765, "retweets": 8234, "replies": 1987, "quotes": 512, "views": 923000},
            "media_urls": ["https://pbs.twimg.com/media/blue_origin_launch.jpg"],
            "topics": ["tech", "space", "aerospace"]
        },
        {
            "id": 1046,
            "author": "Elon Musk",
            "text": "Starship is ready for orbital flight! This will change everything about space exploration and human civilization. Mars, here we come! 🌌",
            "metrics": {"likes": 67890, "retweets": 18765, "replies": 4567, "quotes": 1234, "views": 2300000},
            "media_urls": [],
            "topics": ["tech", "space", "spacex"]
        },
        {
            "id": 1047,
            "author": "Mark Zuckerberg",
            "text": "Threads now has 200M+ monthly active users. The open social web is winning. Thanks to everyone who's been part of this journey! 🧵",
            "metrics": {"likes": 15678, "retweets": 4321, "replies": 1234, "quotes": 345, "views": 567000},
            "media_urls": [],
            "topics": ["tech", "social media", "meta"]
        },
        {
            "id": 1048,
            "author": "Y Combinator",
            "text": "Applications for W26 batch are open! We're especially excited about AI, biotech, and climate tech startups. Apply now: ycombinator.com/apply",
            "metrics": {"likes": 12345, "retweets": 3456, "replies": 789, "quotes": 198, "views": 423000},
            "media_urls": [],
            "topics": ["tech", "startup", "funding"]
        },
        {
            "id": 1049,
            "author": "Stripe",
            "text": "We just processed our trillionth dollar in payments! Thanks to millions of businesses worldwide who trust Stripe. Here's to the next trillion! 💳",
            "metrics": {"likes": 18765, "retweets": 4987, "replies": 1123, "quotes": 289, "views": 645000},
            "media_urls": [],
            "topics": ["tech", "fintech", "payments"]
        },
        {
            "id": 1050,
            "author": "Shopify",
            "text": "Black Friday sales on Shopify merchants reached $9.3B! E-commerce continues to grow. Proud to power millions of entrepreneurs worldwide. 🛍️",
            "metrics": {"likes": 14567, "retweets": 3789, "replies": 987, "quotes": 234, "views": 498000},
            "media_urls": [],
            "topics": ["tech", "ecommerce", "business"]
        },
        {
            "id": 1051,
            "author": "GitHub",
            "text": "GitHub Copilot now has 10M+ developers! AI pair programming is mainstream. 55% of code is now written with AI assistance. The future of coding is here.",
            "metrics": {"likes": 23456, "retweets": 6789, "replies": 1456, "quotes": 389, "views": 712000},
            "media_urls": [],
            "topics": ["tech", "developer tools", "ai"]
        },
        {
            "id": 1052,
            "author": "Vercel",
            "text": "Next.js 15 is out! App Router performance improvements, Turbopack stable, and so much more. The best React framework keeps getting better. ▲",
            "metrics": {"likes": 19876, "retweets": 5234, "replies": 1289, "quotes": 345, "views": 612000},
            "media_urls": [],
            "topics": ["tech", "web development", "javascript"]
        },
        {
            "id": 1053,
            "author": "Cloudflare",
            "text": "We now handle 20% of all internet traffic. Workers AI enables edge computing with GPU acceleration. The internet is getting faster and smarter! ⚡",
            "metrics": {"likes": 16543, "retweets": 4321, "replies": 1034, "quotes": 278, "views": 534000},
            "media_urls": [],
            "topics": ["tech", "cloud", "infrastructure"]
        },
        {
            "id": 1054,
            "author": "Notion",
            "text": "Notion AI is now available to all users! Chat with your workspace, generate content, and automate workflows. The all-in-one workspace just got smarter. 🧠",
            "metrics": {"likes": 21345, "retweets": 5876, "replies": 1432, "quotes": 387, "views": 689000},
            "media_urls": [],
            "topics": ["tech", "productivity", "ai"]
        },
        {
            "id": 1055,
            "author": "Figma",
            "text": "Config 2025 was amazing! AI-powered design tools, Dev Mode improvements, and so much more. Thanks to the 15,000 attendees! 🎨",
            "metrics": {"likes": 17654, "retweets": 4567, "replies": 1123, "quotes": 298, "views": 578000},
            "media_urls": ["https://pbs.twimg.com/media/config_highlights.jpg"],
            "topics": ["tech", "design", "tools"]
        },
        {
            "id": 1056,
            "author": "Linear",
            "text": "Linear is now used by 10,000+ companies. Building the best issue tracking tool for modern software teams. Thanks for the support! 📈",
            "metrics": {"likes": 13456, "retweets": 3456, "replies": 789, "quotes": 198, "views": 445000},
            "media_urls": [],
            "topics": ["tech", "productivity", "software"]
        },
        {
            "id": 1057,
            "author": "Replit",
            "text": "Replit Agent can now build full-stack apps from a prompt. AI-powered coding for everyone. 100M+ projects created! The future of software development. 🤖",
            "metrics": {"likes": 18765, "retweets": 4987, "replies": 1234, "quotes": 334, "views": 623000},
            "media_urls": [],
            "topics": ["tech", "ai", "developer tools"]
        },
        {
            "id": 1058,
            "author": "MongoDB",
            "text": "MongoDB Atlas now supports vector search natively! Build AI applications with your existing database. RAG has never been easier. 🍃",
            "metrics": {"likes": 14567, "retweets": 3789, "replies": 923, "quotes": 245, "views": 478000},
            "media_urls": [],
            "topics": ["tech", "database", "ai"]
        },
        {
            "id": 1059,
            "author": "Supabase",
            "text": "Supabase just raised $80M Series B! Open-source Firebase alternative is growing fast. Thanks to our amazing community! 🚀",
            "metrics": {"likes": 22345, "retweets": 6123, "replies": 1456, "quotes": 389, "views": 723000},
            "media_urls": [],
            "topics": ["tech", "database", "open source", "funding"]
        },

        # Science tweets (IDs 1060-1069)
        {
            "id": 1060,
            "author": "Nature Journal",
            "text": "Breakthrough in quantum computing: New error correction method achieves 99.9% fidelity. This brings us closer to fault-tolerant quantum computers. Paper published today.",
            "metrics": {"likes": 8765, "retweets": 2345, "replies": 567, "quotes": 145, "views": 234000},
            "media_urls": ["https://pbs.twimg.com/media/quantum_diagram.png"],
            "topics": ["science", "quantum computing"]
        },
        {
            "id": 1061,
            "author": "NASA",
            "text": "James Webb Space Telescope discovers Earth-like exoplanet with oxygen-rich atmosphere! JWST continues to revolutionize astronomy. Full results at nasa.gov 🔭",
            "metrics": {"likes": 45678, "retweets": 12345, "replies": 3456, "quotes": 876, "views": 1230000},
            "media_urls": ["https://pbs.twimg.com/media/exoplanet_jwst.jpg"],
            "topics": ["science", "space", "astronomy"]
        },
        {
            "id": 1062,
            "author": "Science Magazine",
            "text": "CRISPR gene therapy successfully cures sickle cell disease in human trial. 42 patients disease-free after 18 months. Historic medical breakthrough!",
            "metrics": {"likes": 23456, "retweets": 6789, "replies": 1456, "quotes": 389, "views": 678000},
            "media_urls": [],
            "topics": ["science", "medicine", "biotech"]
        },
        {
            "id": 1063,
            "author": "CERN",
            "text": "Large Hadron Collider discovers new elementary particle! This could help explain dark matter. Physics community is excited. Details in our press release. ⚛️",
            "metrics": {"likes": 19876, "retweets": 5432, "replies": 1234, "quotes": 334, "views": 567000},
            "media_urls": [],
            "topics": ["science", "physics", "particle physics"]
        },
        {
            "id": 1064,
            "author": "MIT",
            "text": "Our researchers developed a room-temperature superconductor! This could revolutionize energy transmission and quantum computing. Nature paper out tomorrow.",
            "metrics": {"likes": 34567, "retweets": 9876, "replies": 2345, "quotes": 623, "views": 923000},
            "media_urls": [],
            "topics": ["science", "physics", "materials"]
        },
        {
            "id": 1065,
            "author": "SpaceX",
            "text": "Starlink now provides internet to 5M+ customers in 100+ countries! Low-latency satellite internet is changing connectivity worldwide. 🛰️",
            "metrics": {"likes": 28765, "retweets": 7654, "replies": 1876, "quotes": 489, "views": 812000},
            "media_urls": [],
            "topics": ["science", "space", "technology"]
        },
        {
            "id": 1066,
            "author": "NIH",
            "text": "New Alzheimer's drug shows 70% reduction in cognitive decline in Phase 3 trial. Hope for millions of patients worldwide. FDA approval expected Q3 2025.",
            "metrics": {"likes": 18765, "retweets": 5234, "replies": 1456, "quotes": 378, "views": 623000},
            "media_urls": [],
            "topics": ["science", "medicine", "health"]
        },
        {
            "id": 1067,
            "author": "Stanford",
            "text": "Breakthrough in fusion energy: Our reactor achieved net positive energy for 10 seconds! Clean unlimited energy is getting closer. Science paper forthcoming.",
            "metrics": {"likes": 42345, "retweets": 11234, "replies": 2876, "quotes": 723, "views": 1120000},
            "media_urls": [],
            "topics": ["science", "energy", "fusion"]
        },
        {
            "id": 1068,
            "author": "Max Planck Society",
            "text": "Our team observed quantum entanglement over 1,200 km! This breaks all previous records and enables intercontinental quantum communication. 🔬",
            "metrics": {"likes": 14567, "retweets": 3876, "replies": 923, "quotes": 245, "views": 445000},
            "media_urls": [],
            "topics": ["science", "physics", "quantum"]
        },
        {
            "id": 1069,
            "author": "WHO",
            "text": "New malaria vaccine shows 95% efficacy in African trials! This could save millions of lives. Largest vaccination campaign begins next month. Historic moment! 🏥",
            "metrics": {"likes": 38765, "retweets": 10234, "replies": 2456, "quotes": 634, "views": 978000},
            "media_urls": [],
            "topics": ["science", "medicine", "health", "vaccine"]
        },

        # Business/Finance tweets (IDs 1070-1099)
        {
            "id": 1070,
            "author": "Bloomberg",
            "text": "BREAKING: S&P 500 hits all-time high of 6,200 as tech stocks rally. AI boom continues to drive market gains. Analysis at bloomberg.com 📈",
            "metrics": {"likes": 12345, "retweets": 3456, "replies": 789, "quotes": 198, "views": 423000},
            "media_urls": ["https://pbs.twimg.com/media/sp500_chart.png"],
            "topics": ["business", "finance", "stock market"]
        },
        {
            "id": 1071,
            "author": "WSJ",
            "text": "Apple becomes first $4 trillion company. Tim Cook: 'Our best days are ahead.' Stock up 40% YTD driven by Vision Pro and AI services. 🍎",
            "metrics": {"likes": 18765, "retweets": 5234, "replies": 1234, "quotes": 334, "views": 578000},
            "media_urls": [],
            "topics": ["business", "tech", "apple"]
        },
        {
            "id": 1072,
            "author": "Financial Times",
            "text": "Tesla's autonomous taxi service launches in 10 US cities. $TSLA surges 25% on the news. Disruption of ride-sharing industry begins. 🚗",
            "metrics": {"likes": 15678, "retweets": 4321, "replies": 1087, "quotes": 289, "views": 512000},
            "media_urls": [],
            "topics": ["business", "automotive", "tesla"]
        },
        {
            "id": 1073,
            "author": "Warren Buffett",
            "text": "At 94, I'm still learning. The best investment you can make is in yourself. Berkshire's annual letter is out - read about our AI investments! 📖",
            "metrics": {"likes": 45678, "retweets": 12345, "replies": 2876, "quotes": 723, "views": 1120000},
            "media_urls": [],
            "topics": ["business", "investment", "wisdom"]
        },
        {
            "id": 1074,
            "author": "Goldman Sachs",
            "text": "AI is expected to boost global GDP by $7 trillion over the next decade. Our latest research report on the AI economy is now available. 💼",
            "metrics": {"likes": 9876, "retweets": 2678, "replies": 645, "quotes": 167, "views": 334000},
            "media_urls": [],
            "topics": ["business", "ai", "economy"]
        },
        {
            "id": 1075,
            "author": "McKinsey",
            "text": "60% of jobs will be augmented by AI within 3 years. The future of work is human-AI collaboration. Download our full report on workforce transformation. 📊",
            "metrics": {"likes": 11234, "retweets": 3012, "replies": 734, "quotes": 189, "views": 389000},
            "media_urls": [],
            "topics": ["business", "ai", "future of work"]
        },
        {
            "id": 1076,
            "author": "Forbes",
            "text": "The world's billionaires list 2025 is out! Tech founders dominate the top 10. Total billionaire wealth reaches $15 trillion. See the full list at forbes.com 💰",
            "metrics": {"likes": 14567, "retweets": 3987, "replies": 1023, "quotes": 267, "views": 467000},
            "media_urls": [],
            "topics": ["business", "wealth", "rankings"]
        },
        {
            "id": 1077,
            "author": "Andreessen Horowitz",
            "text": "AI startups raised $97B in 2024, up 320% YoY. We're doubling down with a new $6.6B fund focused on AI infrastructure. The next decade belongs to AI builders! 🚀",
            "metrics": {"likes": 16543, "retweets": 4521, "replies": 1145, "quotes": 298, "views": 534000},
            "media_urls": [],
            "topics": ["business", "vc", "ai", "funding"]
        },
        {
            "id": 1078,
            "author": "Sequoia Capital",
            "text": "OpenAI's $150B valuation makes it the most valuable private company. We're proud investors since 2019. The AI revolution is just beginning. 🌟",
            "metrics": {"likes": 19876, "retweets": 5432, "replies": 1345, "quotes": 356, "views": 612000},
            "media_urls": [],
            "topics": ["business", "vc", "ai", "valuation"]
        },
        {
            "id": 1079,
            "author": "The Economist",
            "text": "China's GDP growth slows to 4.2% in Q1 2025. Analysts attribute it to property sector challenges and trade tensions. Full analysis in this week's issue. 🌏",
            "metrics": {"likes": 8765, "retweets": 2345, "replies": 567, "quotes": 145, "views": 267000},
            "media_urls": [],
            "topics": ["business", "economy", "china"]
        },
        {
            "id": 1080,
            "author": "CNBC",
            "text": "Federal Reserve holds interest rates steady at 4.25-4.50%. Chair Powell: 'Inflation is moderating, but we remain vigilant.' Markets rally on the news. 📊",
            "metrics": {"likes": 13456, "retweets": 3678, "replies": 834, "quotes": 212, "views": 445000},
            "media_urls": [],
            "topics": ["business", "finance", "monetary policy"]
        },
        {
            "id": 1081,
            "author": "Reuters",
            "text": "Microsoft acquires Hugging Face for $25B in largest AI deal ever. Satya Nadella: 'Open-source AI is critical to our strategy.' $MSFT up 8%. 🤝",
            "metrics": {"likes": 22345, "retweets": 6234, "replies": 1567, "quotes": 412, "views": 734000},
            "media_urls": [],
            "topics": ["business", "tech", "m&a", "ai"]
        },
        {
            "id": 1082,
            "author": "Harvard Business Review",
            "text": "New research: Companies using AI see 40% productivity gains but face cultural resistance. Leadership is key to successful AI adoption. Read the full study. 📚",
            "metrics": {"likes": 10234, "retweets": 2876, "replies": 678, "quotes": 167, "views": 356000},
            "media_urls": [],
            "topics": ["business", "ai", "management"]
        },
        {
            "id": 1083,
            "author": "Elon Musk",
            "text": "X (Twitter) now has 800M monthly active users. Free speech is thriving. Excited to announce new features coming next month! 🐦",
            "metrics": {"likes": 56789, "retweets": 15234, "replies": 3876, "quotes": 987, "views": 1890000},
            "media_urls": [],
            "topics": ["business", "social media", "tech"]
        },
        {
            "id": 1084,
            "author": "CB Insights",
            "text": "Tech IPO market is heating up! 42 tech companies went public in Q1 2025, up 150% YoY. AI and cybersecurity startups lead the pack. 📈",
            "metrics": {"likes": 11876, "retweets": 3234, "replies": 756, "quotes": 189, "views": 398000},
            "media_urls": [],
            "topics": ["business", "ipo", "tech"]
        },
        {
            "id": 1085,
            "author": "PitchBook",
            "text": "Late-stage funding is back! $43B deployed in Q1, highest since 2021. Investors are confident again. Full quarterly report available now. 💼",
            "metrics": {"likes": 9876, "retweets": 2567, "replies": 634, "quotes": 156, "views": 312000},
            "media_urls": [],
            "topics": ["business", "vc", "funding"]
        },
        {
            "id": 1086,
            "author": "BlackRock",
            "text": "We're launching a $5B AI infrastructure fund. The buildout of AI data centers represents the largest infrastructure opportunity in decades. 🏗️",
            "metrics": {"likes": 14567, "retweets": 3987, "replies": 923, "quotes": 245, "views": 478000},
            "media_urls": [],
            "topics": ["business", "ai", "infrastructure", "investment"]
        },
        {
            "id": 1087,
            "author": "SoftBank",
            "text": "Vision Fund 3 closes at $108B, our largest fund yet! Focusing on AI, robotics, and biotech. The Age of AI requires bold investments. 🌐",
            "metrics": {"likes": 12876, "retweets": 3456, "replies": 789, "quotes": 198, "views": 423000},
            "media_urls": [],
            "topics": ["business", "vc", "ai"]
        },
        {
            "id": 1088,
            "author": "Deloitte",
            "text": "AI implementation is top priority for 87% of Fortune 500 CEOs in 2025. Our Global AI Survey reveals the boardroom agenda. Download the report. 📑",
            "metrics": {"likes": 10234, "retweets": 2765, "replies": 645, "quotes": 167, "views": 345000},
            "media_urls": [],
            "topics": ["business", "ai", "consulting"]
        },
        {
            "id": 1089,
            "author": "Accenture",
            "text": "Generative AI could add $4.4T annually to the global economy. Our latest research explores AI's transformative impact across industries. 🌍",
            "metrics": {"likes": 11765, "retweets": 3123, "replies": 734, "quotes": 189, "views": 378000},
            "media_urls": [],
            "topics": ["business", "ai", "consulting"]
        },
        {
            "id": 1090,
            "author": "Nvidia",
            "text": "NVIDIA stock splits 10-for-1! Market cap now $3.5T. Jensen: 'We're just getting started with AI.' Thanks to our customers and shareholders! 🎉",
            "metrics": {"likes": 28765, "retweets": 7891, "replies": 1987, "quotes": 512, "views": 845000},
            "media_urls": [],
            "topics": ["business", "tech", "stock market"]
        },
        {
            "id": 1091,
            "author": "AMD",
            "text": "AMD MI300 GPUs are now powering major AI labs. Our market share in AI accelerators grows to 35%! Competition drives innovation. 🔴",
            "metrics": {"likes": 16543, "retweets": 4321, "replies": 1087, "quotes": 289, "views": 534000},
            "media_urls": [],
            "topics": ["business", "tech", "hardware", "ai"]
        },
        {
            "id": 1092,
            "author": "Intel",
            "text": "Intel 18A process node delivers as promised! We're back in the semiconductor race. Major customer wins to be announced next quarter. 💪",
            "metrics": {"likes": 13456, "retweets": 3678, "replies": 845, "quotes": 223, "views": 456000},
            "media_urls": [],
            "topics": ["business", "tech", "semiconductors"]
        },
        {
            "id": 1093,
            "author": "TSMC",
            "text": "Our 2nm chip production begins Q2 2025! Leading-edge semiconductor manufacturing continues. Proud to enable the AI revolution. 🏭",
            "metrics": {"likes": 17654, "retweets": 4567, "replies": 1134, "quotes": 298, "views": 589000},
            "media_urls": [],
            "topics": ["business", "tech", "semiconductors"]
        },
        {
            "id": 1094,
            "author": "Samsung",
            "text": "Galaxy AI features now on 500M+ devices worldwide! On-device AI is the future. Our partnership with Google brings the best of both worlds. 📱",
            "metrics": {"likes": 19876, "retweets": 5234, "replies": 1289, "quotes": 345, "views": 645000},
            "media_urls": [],
            "topics": ["business", "tech", "mobile", "ai"]
        },
        {
            "id": 1095,
            "author": "Oracle",
            "text": "Oracle Cloud Infrastructure revenue up 65% YoY! Our AI infrastructure wins against hyperscalers continue. Enterprise AI runs on OCI. ☁️",
            "metrics": {"likes": 11234, "retweets": 2987, "replies": 723, "quotes": 178, "views": 378000},
            "media_urls": [],
            "topics": ["business", "cloud", "enterprise"]
        },
        {
            "id": 1096,
            "author": "Salesforce",
            "text": "Einstein GPT is now used by 80% of our customers! AI-powered CRM is transforming sales and service. Dreamforce 2025 registration opens today! 🤖",
            "metrics": {"likes": 14567, "retweets": 3789, "replies": 934, "quotes": 245, "views": 467000},
            "media_urls": [],
            "topics": ["business", "saas", "ai", "crm"]
        },
        {
            "id": 1097,
            "author": "ServiceNow",
            "text": "Workflow AI drives 50% productivity gains for IT teams. Our customers are automating everything. The platform of platforms just got smarter. ⚡",
            "metrics": {"likes": 12876, "retweets": 3345, "replies": 812, "quotes": 201, "views": 412000},
            "media_urls": [],
            "topics": ["business", "saas", "ai", "enterprise"]
        },
        {
            "id": 1098,
            "author": "Workday",
            "text": "Workday AI skills engine helps 60M+ workers find career paths. The future of HR is intelligent. Proud to lead workforce transformation! 👥",
            "metrics": {"likes": 11345, "retweets": 2976, "replies": 689, "quotes": 167, "views": 367000},
            "media_urls": [],
            "topics": ["business", "saas", "hr", "ai"]
        },
        {
            "id": 1099,
            "author": "Snowflake",
            "text": "Snowflake Cortex AI delivers native LLM capabilities in your data cloud. Build AI apps without moving data. The data cloud gets intelligent! ❄️",
            "metrics": {"likes": 15234, "retweets": 4012, "replies": 978, "quotes": 256, "views": 489000},
            "media_urls": [],
            "topics": ["business", "data", "ai", "cloud"]
        }
    ]

    def __init__(self):
        """Initialize the mock adapter."""
        pass

    async def fetch(
        self,
        query: str,
        start_date: datetime,
        end_date: datetime,
        max_items: int = 100,
        since_id: Optional[str] = None
    ) -> List[RawItem]:
        """
        Fetch mock tweets based on the query.

        Args:
            query: Search query (used to select topic)
            start_date: Start of time window
            end_date: End of time window
            max_items: Maximum items to return
            since_id: Optional tweet ID to fetch tweets after (for incremental collection)

        Returns:
            List of RawItem objects (filtered by since_id if provided)
        """
        # Select appropriate mock data based on query
        query_lower = query.lower()
        filtered_data = []

        if "ai" in query_lower or "machine learning" in query_lower or "gpt" in query_lower:
            filtered_data = [t for t in self.MOCK_TWEETS if any(topic in ["ai", "machine learning", "gpt"] for topic in t.get("topics", []))]
        elif "crypto" in query_lower or "bitcoin" in query_lower or "ethereum" in query_lower:
            filtered_data = [t for t in self.MOCK_TWEETS if any(topic in ["crypto", "bitcoin", "ethereum"] for topic in t.get("topics", []))]
        elif "tech" in query_lower or "startup" in query_lower or "software" in query_lower:
            filtered_data = [t for t in self.MOCK_TWEETS if any(topic in ["tech", "startup", "software"] for topic in t.get("topics", []))]
        else:
            filtered_data = [t for t in self.MOCK_TWEETS if "default" in t.get("topics", [])]

        # Filter by since_id if provided
        if since_id:
            try:
                since_id_int = int(since_id)
                filtered_data = [tweet for tweet in filtered_data if tweet["id"] > since_id_int]
                logger.info(f"Filtered to {len(filtered_data)} tweets after since_id={since_id}")
            except ValueError:
                logger.warning(f"Invalid since_id format: {since_id}, ignoring filter")
                # Continue without since_id filtering

        if not filtered_data:
            logger.info("No tweets available after filtering")
            return []

        # Generate items from filtered data
        items = []
        num_items = min(max_items, len(filtered_data))

        for i in range(num_items):
            tweet = filtered_data[i]

            # Vary timestamps within the window
            time_diff = end_date - start_date
            total_seconds = int(time_diff.total_seconds())
            if total_seconds > 0:
                random_seconds = random.randint(0, total_seconds)
                created_at = start_date + timedelta(seconds=random_seconds)
            else:
                created_at = start_date

            # Create item with NUMERIC source_id (CRITICAL FIX)
            item = RawItem(
                source_id=str(tweet["id"]),  # e.g., "1000", "1001" - MUST be numeric
                author=tweet["author"],
                text=tweet["text"],
                url=f"https://twitter.com/{tweet['author'].lower().replace(' ', '')}/status/{tweet['id']}",
                created_at=created_at,
                media_urls=tweet.get("media_urls", []),
                metrics=tweet["metrics"]
            )
            items.append(item)

        logger.info(f"Generated {len(items)} mock items")
        return items
