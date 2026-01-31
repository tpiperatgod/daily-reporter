"""Prompt templates for LLM interactions."""

from datetime import datetime


# Digest generation prompt
DIGEST_PROMPT_TEMPLATE = """You are an expert content analyst specializing in social media intelligence. Your task is to analyze a collection of tweets/posts about "{topic}" and create a comprehensive, insightful digest.

## Time Window
- Start: {time_window_start}
- End: {time_window_end}
- Total Posts: {total_items}

## Posts to Analyze
{posts}

## Your Task

Create a structured digest that:

1. **Identifies Key Themes**: What are the main topics, trends, or discussions?
2. **Highlights Important Developments**: What significant news, announcements, or breakthroughs occurred?
3. **Summarizes Community Sentiment**: What is the overall tone and opinion of the community?
4. **Extracts Actionable Insights**: What valuable information can be derived?

## Response Format

You must respond with valid JSON in this exact format:

```json
{{
  "headline": "A compelling 10-15 word headline summarizing the most important development",
  "highlights": [
    {{
      "title": "Brief title for this highlight (3-8 words)",
      "summary": "2-3 sentence summary of this key point, including context and why it matters",
      "representative_urls": ["url1", "url2"],
      "score": 8
    }}
  ],
  "themes": ["theme1", "theme2", "theme3"],
  "sentiment": "positive|neutral|negative|mixed",
  "stats": {{
    "total_posts_analyzed": 0,
    "unique_authors": 0,
    "total_engagement": 0,
    "avg_engagement_per_post": 0
  }}
}}
```

## Guidelines

- Create 3-7 highlights based on the volume and importance of content
- Score each highlight 1-10 based on significance (10 = most important)
- Select 2-4 representative URLs per highlight from the provided posts
- Keep summaries concise but informative
- Focus on insights, not just repeating information
- If sentiment is unclear, default to "neutral"
- Extract themes as short, descriptive phrases (2-4 words each)

Analyze the posts carefully and provide your JSON response:"""


def build_digest_prompt(
    topic: str,
    time_window_start: datetime,
    time_window_end: datetime,
    posts: list[dict],
    total_items: int
) -> str:
    """
    Build the digest generation prompt.

    Args:
        topic: Topic name
        time_window_start: Start of time window
        time_window_end: End of time window
        posts: List of post dictionaries with text, author, url
        total_items: Total number of items

    Returns:
        Formatted prompt string
    """
    # Format posts for the prompt
    formatted_posts = []
    for i, post in enumerate(posts, 1):
        post_text = f"""
Post {i}:
Author: {post.get('author', 'Unknown')}
Text: {post.get('text', '')}
URL: {post.get('url', 'N/A')}
Engagement: {post.get('engagement_score', 0)}
"""
        formatted_posts.append(post_text)

    posts_section = "\n".join(formatted_posts)

    return DIGEST_PROMPT_TEMPLATE.format(
        topic=topic,
        time_window_start=time_window_start.strftime("%Y-%m-%d %H:%M"),
        time_window_end=time_window_end.strftime("%Y-%m-%d %H:%M"),
        total_items=total_items,
        posts=posts_section
    )
