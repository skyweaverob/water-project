"""Embedding service for fact_sheet_chunks. Voyage AI (voyage-3) by default."""
from __future__ import annotations

import asyncio
from typing import Sequence

import voyageai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

_settings = get_settings()


_vo_client: voyageai.AsyncClient | None = None


def _client() -> voyageai.AsyncClient:
    global _vo_client
    if _vo_client is None:
        _vo_client = voyageai.AsyncClient(api_key=_settings.voyage_api_key)
    return _vo_client


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def embed_texts(texts: Sequence[str], input_type: str = "document") -> list[list[float]]:
    """Embed a list of texts. Voyage handles its own batching internally."""
    if not texts:
        return []
    response = await _client().embed(
        texts=list(texts),
        model=_settings.claude_model_embed,
        input_type=input_type,
    )
    return response.embeddings


async def embed_query(text: str) -> list[float]:
    out = await embed_texts([text], input_type="query")
    return out[0]
