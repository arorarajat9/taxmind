"""Local knowledge base — runs the citation/grounding demo with no Azure keys.

Chunks the bundled public GST Act text by heading, then retrieves with a simple
TF-weighted token-overlap score. This is intentionally transparent and
dependency-free so the deadline-day demo is reproducible. The exact same
:class:`KnowledgeResult` is later served by Foundry IQ in Azure mode.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

from backend.config import GST_SOURCES_DIR
from backend.foundry_iq.base import KnowledgeBase, KnowledgeResult
from backend.ontology.entities import Citation

_WORD = re.compile(r"[a-z0-9]+")
_STOP = {
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "is", "are",
    "be", "as", "by", "it", "this", "that", "with", "any", "such", "shall",
    "under", "section", "credit", "input", "tax", "gst", "what", "which", "where",
}


def _tokens(text: str) -> list[str]:
    return [w for w in _WORD.findall(text.lower()) if w not in _STOP and len(w) > 1]


@dataclass
class _Chunk:
    section: str
    title: str
    text: str
    source: str
    tokens: list[str]


def _extract_section(title: str) -> str:
    """Pull a 'Section 17(5)(b)(i)' style label out of a heading, else the title."""
    m = re.search(r"Section\s+[0-9]+[A-Za-z0-9()]*", title)
    return m.group(0) if m else title.strip()


class LocalKnowledgeBase(KnowledgeBase):
    name = "local-gst-kb"

    def __init__(self, sources_dir: Path | None = None) -> None:
        self._chunks: list[_Chunk] = []
        self._df: dict[str, int] = {}
        self._load(sources_dir or GST_SOURCES_DIR)

    def _load(self, sources_dir: Path) -> None:
        for path in sorted(Path(sources_dir).glob("*.md")):
            self._chunk_file(path)
        # document frequency for idf weighting
        for chunk in self._chunks:
            for tok in set(chunk.tokens):
                self._df[tok] = self._df.get(tok, 0) + 1

    def _chunk_file(self, path: Path) -> None:
        source = path.stem.replace("-", " ")
        text = path.read_text(encoding="utf-8")
        # split on markdown headings (## or ###), keeping the heading
        parts = re.split(r"^(#{2,3}\s+.*)$", text, flags=re.MULTILINE)
        # parts = [pre, heading1, body1, heading2, body2, ...]
        for i in range(1, len(parts), 2):
            heading = parts[i].lstrip("#").strip()
            body = parts[i + 1].strip() if i + 1 < len(parts) else ""
            if not body:
                continue
            block = f"{heading}\n{body}"
            self._chunks.append(
                _Chunk(
                    section=_extract_section(heading),
                    title=heading,
                    text=block,
                    source=source,
                    tokens=_tokens(block),
                )
            )

    def _score(self, q_tokens: list[str], chunk: _Chunk) -> float:
        if not chunk.tokens:
            return 0.0
        n = len(self._chunks)
        chunk_counts: dict[str, int] = {}
        for t in chunk.tokens:
            chunk_counts[t] = chunk_counts.get(t, 0) + 1
        score = 0.0
        for qt in set(q_tokens):
            if qt in chunk_counts:
                idf = math.log(1 + n / (1 + self._df.get(qt, 0)))
                tf = chunk_counts[qt] / len(chunk.tokens)
                score += idf * (1 + tf)
        # small boost when the query literally names a section/clause
        for qt in q_tokens:
            if qt in chunk.section.lower():
                score += 1.5
        return score

    def query(self, question: str, top_k: int = 3) -> KnowledgeResult:
        q_tokens = _tokens(question)
        # also fold in raw digits/letters from explicit section refs like "17(5)"
        q_tokens += _WORD.findall(question.lower())
        scored = sorted(
            ((self._score(q_tokens, c), c) for c in self._chunks),
            key=lambda x: x[0],
            reverse=True,
        )
        top = [(s, c) for s, c in scored[:top_k] if s > 0]
        if not top:
            return KnowledgeResult(
                question=question,
                answer="No grounding found in the GST knowledge base for this query.",
                confidence=0.0,
                backend="local",
            )

        best_score = top[0][0]
        # normalise to a 0..1 confidence; calibrated so a strong section hit clears
        # the CONFIDENCE_FLOOR while weak/ambiguous hits fall under it.
        confidence = max(0.0, min(1.0, best_score / (best_score + 4.0)))

        citations = [
            Citation(
                section=c.section,
                snippet=_first_sentences(c.text),
                source=c.source,
                confidence=max(0.0, min(1.0, s / (best_score + 4.0))),
            )
            for s, c in top
        ]
        answer = top[0][1].text.strip()
        return KnowledgeResult(
            question=question,
            answer=answer,
            citations=citations,
            confidence=confidence,
            backend="local",
        )


def _first_sentences(text: str, max_chars: int = 320) -> str:
    body = text.split("\n", 1)[-1].strip() if "\n" in text else text
    body = re.sub(r"\s+", " ", body)
    if len(body) <= max_chars:
        return body
    cut = body[:max_chars]
    return cut.rsplit(".", 1)[0].strip() + "."
