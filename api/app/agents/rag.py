"""RAG over EPA fact-sheet chunks.

retrieve(question, k=8): pgvector cosine-similarity search across `fact_sheet_chunks`.
answer(question): assembles top-k chunks into a Claude prompt and streams an answer with
inline citation markers ⟨1⟩ ⟨2⟩ that map back to (chemical, page, section).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.anthropic_client import get_client
from app.agents.embeddings import embed_query
from app.config import get_settings
from app.models import Chemical, FactSheetChunk

_settings = get_settings()


@dataclass
class Citation:
    n: int
    chemical: str
    page: int | None
    section: str | None
    snippet: str


@dataclass
class Retrieval:
    citations: list[Citation]
    context_block: str


async def retrieve(session: AsyncSession, question: str, k: int = 8) -> Retrieval:
    qvec = await embed_query(question)

    stmt = (
        select(FactSheetChunk, Chemical.name)
        .join(Chemical, Chemical.id == FactSheetChunk.chemical_id)
        .order_by(FactSheetChunk.embedding.cosine_distance(qvec))
        .limit(k)
    )
    rows = (await session.execute(stmt)).all()

    citations = []
    parts = []
    for i, (chunk, chem_name) in enumerate(rows, start=1):
        snippet = chunk.text.strip().replace("\n\n", "\n")[:400]
        citations.append(
            Citation(n=i, chemical=chem_name, page=chunk.page_num, section=chunk.section, snippet=snippet)
        )
        parts.append(
            f"[{i}] Chemical: {chem_name}; Section: {chunk.section}; Page: {chunk.page_num}\n{chunk.text}"
        )
    return Retrieval(citations=citations, context_block="\n\n---\n\n".join(parts))


SYSTEM_PROMPT = """You answer questions about water treatment chemicals using ONLY the provided context excerpts. You are advising a procurement officer or plant superintendent — be precise, calm, and operational.

Citation rules:
- After any factual claim, append a citation marker like ⟨1⟩ that refers to the numbered context excerpt.
- Use multiple citations like ⟨1, 3⟩ when several excerpts support the claim.
- If the context does not answer the question, say so explicitly. Do not fabricate.
- Do not include a "References" section — citations are inline and the UI renders them as superscripts.

Tone: short paragraphs, no headers unless the question is genuinely multi-part, no marketing language."""


async def answer_stream(session: AsyncSession, question: str) -> AsyncIterator[str | dict]:
    """Async generator yielding text chunks. The first yield is the citations dict."""
    retrieval = await retrieve(session, question, k=8)

    yield {
        "type": "citations",
        "citations": [
            {
                "n": c.n,
                "chemical": c.chemical,
                "page": c.page,
                "section": c.section,
                "snippet": c.snippet,
            }
            for c in retrieval.citations
        ],
    }

    client = get_client()
    async with client.messages.stream(
        model=_settings.claude_model_synthesis,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\nContext excerpts (numbered for citation):\n\n"
                    f"{retrieval.context_block}\n\nAnswer concisely with inline ⟨n⟩ citations."
                ),
            }
        ],
    ) as stream:
        async for text in stream.text_stream:
            yield text
