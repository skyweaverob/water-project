"""Section-aware chunker for EPA fact sheets.

Splits each ExtractedSection into ~600-word chunks (with 80-word overlap) for embedding.
Chunks preserve section attribution so citations can point to a section + page.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.agents.extraction import ExtractedSection


@dataclass
class Chunk:
    page_num: int
    section: str
    text: str


def chunk_sections(sections: list[ExtractedSection], target_words: int = 600, overlap: int = 80) -> list[Chunk]:
    chunks: list[Chunk] = []
    for sec in sections:
        words = sec.text.split()
        if not words:
            continue
        if len(words) <= target_words:
            chunks.append(Chunk(page_num=sec.page_num, section=sec.section, text=sec.text))
            continue

        step = target_words - overlap
        for start in range(0, len(words), step):
            piece = words[start : start + target_words]
            if len(piece) < 50:
                break
            chunks.append(
                Chunk(page_num=sec.page_num, section=sec.section, text=" ".join(piece))
            )
    return chunks
