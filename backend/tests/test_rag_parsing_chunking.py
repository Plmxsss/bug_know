"""Tests for deterministic document parsing and chunk construction."""

from pathlib import Path

import pytest
from pypdf import PdfWriter

from app.rag.chunking import TextChunker
from app.rag.parsing import DocumentParser, ParsedSection, clean_text


def test_clean_text_preserves_paragraphs_without_whitespace_noise() -> None:
    """Line endings and repeated spaces should not create unstable chunks."""

    assert clean_text(" A   line \r\n\r\n\r\n  B\tline ") == "A line\n\nB line"


def test_markdown_parser_keeps_heading_locators(tmp_path: Path) -> None:
    """Each Markdown heading should become an independently citable section."""

    path = tmp_path / "source.md"
    path.write_text(
        "# Main\n\nIntro text.\n\n## Damage\n\nLeaf damage.",
        encoding="utf-8",
    )

    sections = DocumentParser().parse(path, file_type="md")

    assert [section.heading for section in sections] == ["Main", "Damage"]
    assert sections[1].locator == "heading:Damage"


def test_chunker_is_bounded_deterministic_and_hashed() -> None:
    """The same parsed text must always yield the same chunks and hashes."""

    sections = (
        ParsedSection(
            heading="Damage",
            locator="heading:Damage",
            content=("first paragraph " * 20) + "\n\n" + ("second paragraph " * 20),
        ),
    )
    chunker = TextChunker(chunk_size=220, overlap=30)

    first = chunker.split(sections)
    second = chunker.split(sections)

    assert first == second
    assert len(first) > 1
    assert all(len(chunk.content) <= 220 for chunk in first)
    assert [chunk.chunk_index for chunk in first] == list(range(len(first)))
    assert all(len(chunk.content_sha256) == 64 for chunk in first)


def test_pdf_without_extractable_text_is_rejected(tmp_path: Path) -> None:
    """Scanned or blank PDFs need OCR instead of silently indexing nothing."""

    path = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with path.open("wb") as output:
        writer.write(output)

    with pytest.raises(ValueError, match="no extractable text"):
        DocumentParser().parse(path, file_type="pdf")
