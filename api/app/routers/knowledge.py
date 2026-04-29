from __future__ import annotations

import json
import time
from typing import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.rag import answer_stream
from app.auth import resolve_tenant
from app.db import get_session
from app.models import QnaQuery, Tenant


router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class QnaIn(BaseModel):
    question: str


@router.post("/ask")
async def ask(
    payload: QnaIn,
    tenant: Tenant = Depends(resolve_tenant),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    started = time.perf_counter()

    async def gen() -> AsyncIterator[bytes]:
        citations: list[dict] = []
        answer_parts: list[str] = []
        async for chunk in answer_stream(session, payload.question):
            if isinstance(chunk, dict) and chunk.get("type") == "citations":
                citations = chunk["citations"]
                yield (json.dumps({"type": "citations", "citations": citations}) + "\n").encode("utf-8")
            else:
                text = chunk if isinstance(chunk, str) else ""
                answer_parts.append(text)
                yield (json.dumps({"type": "delta", "text": text}) + "\n").encode("utf-8")

        latency_ms = (time.perf_counter() - started) * 1000
        record = QnaQuery(
            tenant_id=tenant.id,
            question=payload.question,
            answer="".join(answer_parts),
            citations=citations,
            latency_ms=latency_ms,
            model_used="synthesis",
        )
        session.add(record)
        await session.commit()
        yield (json.dumps({"type": "done", "latency_ms": latency_ms}) + "\n").encode("utf-8")

    return StreamingResponse(gen(), media_type="application/x-ndjson")
