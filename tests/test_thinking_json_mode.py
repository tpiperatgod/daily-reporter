import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.services.llm.client import LLMClient


class _DummyEmbeddingProvider:
    async def generate_embedding(self, text: str) -> list[float]:
        return [0.1]

    async def generate_embeddings_batch(self, texts: list[str], batch_size: int) -> list[list[float]]:
        return [[0.1] for _ in texts]


@pytest_asyncio.fixture
async def llm_client():
    client = LLMClient(embedding_provider=_DummyEmbeddingProvider())
    try:
        yield client
    finally:
        await client.close()


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ('{"ok": true}', {"ok": True}),
        (
            '<thinking>analyzing...</thinking>\n{"headline": "H", "highlights": [], "themes": [], "sentiment": "neutral", "stats": {"total_posts_analyzed": 0}}',
            {
                "headline": "H",
                "highlights": [],
                "themes": [],
                "sentiment": "neutral",
                "stats": {"total_posts_analyzed": 0},
            },
        ),
        (
            '```json\n{"headline": "H", "highlights": [], "themes": [], "sentiment": "neutral", "stats": {"total_posts_analyzed": 0}}\n```',
            {
                "headline": "H",
                "highlights": [],
                "themes": [],
                "sentiment": "neutral",
                "stats": {"total_posts_analyzed": 0},
            },
        ),
        (
            '{"error": "I need to analyze this carefully step by step."}\n\n{"result": "success"}',
            {"result": "success"},
        ),
    ],
)
def test_extract_json_from_content_handles_common_wrappers(llm_client: LLMClient, content: str, expected: dict) -> None:
    assert llm_client._extract_json_from_content(content) == expected


def test_extract_json_from_content_rejects_thinking_only_json(llm_client: LLMClient) -> None:
    content = '{"error": "I need to analyze this carefully and process this step by step."}'
    with pytest.raises(json.JSONDecodeError):
        llm_client._extract_json_from_content(content)


@pytest.mark.asyncio
async def test_call_llm_json_uses_smart_parsing_without_thinking_controls(llm_client: LLMClient) -> None:
    response_payload = {
        "choices": [
            {
                "message": {
                    "content": '<thinking>Analyzing...</thinking>\n```json\n{"status": "ok"}\n```',
                }
            }
        ]
    }

    with patch.object(llm_client.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = response_payload
        mock_post.return_value = mock_response

        result = await llm_client._call_llm_json("test prompt")

    assert result == {"status": "ok"}
    payload = mock_post.call_args.kwargs["json"]
    assert "thinking" not in payload
    assert "extended_thinking" not in payload
    assert "disable_thinking" not in payload
