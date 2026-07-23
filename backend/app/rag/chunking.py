"""Split parsed sections into deterministic, hash-addressable text chunks."""

from dataclasses import dataclass
from hashlib import sha256

from app.rag.parsing import ParsedSection


@dataclass(frozen=True, slots=True)
class TextChunk:
    """One embedding input with stable source and integrity metadata."""

    chunk_index: int
    heading: str | None
    locator: str
    content: str
    content_sha256: str


class TextChunker:
    """Build bounded character chunks without crossing source sections."""

    def __init__(self, *, chunk_size: int, overlap: int) -> None:
        if chunk_size < 200:
            raise ValueError("chunk_size must be at least 200 characters.")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be non-negative and smaller than chunk_size.")
        self._chunk_size = chunk_size
        self._overlap = overlap

    def split(self, sections: tuple[ParsedSection, ...]) -> tuple[TextChunk, ...]:
        """Split all sections and assign one sequence of document-wide indexes."""

        chunks: list[TextChunk] = []
        for section in sections:
            for content in self._split_section(section):
                digest = sha256(content.encode("utf-8")).hexdigest()
                chunks.append(
                    TextChunk(
                        chunk_index=len(chunks),
                        heading=section.heading,
                        locator=section.locator,
                        content=content,
                        content_sha256=digest,
                    )
                )
        return tuple(chunks)

    def _split_section(self, section: ParsedSection) -> list[str]:
        """Prefer paragraph boundaries and use character windows when necessary."""

        prefix = f"{section.heading}\n\n" if section.heading else ""
        body_limit = self._chunk_size - len(prefix)
        if body_limit <= self._overlap:
            raise ValueError("The section heading leaves no usable chunk capacity.")

        paragraphs = [
            paragraph.strip()
            for paragraph in section.content.split("\n\n")
            if paragraph.strip()
        ]
        bodies: list[str] = []
        current = ""
        for paragraph in paragraphs:
            candidate = f"{current}\n\n{paragraph}" if current else paragraph
            if len(candidate) <= body_limit:
                current = candidate
                continue
            if current:
                bodies.append(current)
                current = self._tail(current)
            candidate = f"{current}\n\n{paragraph}" if current else paragraph
            while len(candidate) > body_limit:
                bodies.append(candidate[:body_limit].rstrip())
                candidate = candidate[body_limit - self._overlap :].lstrip()
            current = candidate
        if current:
            bodies.append(current)
        return [f"{prefix}{body}".strip() for body in bodies if body.strip()]

    def _tail(self, content: str) -> str:
        """Keep a small suffix that provides context to the next chunk."""

        if self._overlap == 0:
            return ""
        return content[-self._overlap :].lstrip()
