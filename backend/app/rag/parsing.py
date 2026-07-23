"""Extract clean, locatable text sections from supported source files."""

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass(frozen=True, slots=True)
class ParsedSection:
    """One source section with a citation-friendly locator."""

    heading: str | None
    locator: str
    content: str


def clean_text(value: str) -> str:
    """Normalize line endings and noisy whitespace while preserving paragraphs."""

    value = value.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in value.splitlines()]
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


class DocumentParser:
    """Dispatch source extraction by the validated database file type."""

    def parse(self, path: Path, *, file_type: str) -> tuple[ParsedSection, ...]:
        """Return non-empty sections or raise when no reliable text exists."""

        if file_type == "pdf":
            sections = self._parse_pdf(path)
        elif file_type == "md":
            sections = self._parse_markdown(path)
        elif file_type == "txt":
            content = clean_text(path.read_text(encoding="utf-8"))
            sections = (
                ParsedSection(heading=None, locator="document", content=content),
            )
        else:
            raise ValueError(f"Unsupported document file type: {file_type}")

        non_empty = tuple(section for section in sections if section.content)
        if not non_empty:
            raise ValueError("The document contains no extractable text.")
        return non_empty

    @staticmethod
    def _parse_pdf(path: Path) -> tuple[ParsedSection, ...]:
        """Extract each PDF page separately so citations retain page numbers."""

        reader = PdfReader(path)
        return tuple(
            ParsedSection(
                heading=f"Page {page_number}",
                locator=f"page:{page_number}",
                content=clean_text(page.extract_text() or ""),
            )
            for page_number, page in enumerate(reader.pages, start=1)
        )

    @staticmethod
    def _parse_markdown(path: Path) -> tuple[ParsedSection, ...]:
        """Split Markdown at ATX headings while keeping heading hierarchy text."""

        sections: list[ParsedSection] = []
        heading: str | None = None
        body_lines: list[str] = []

        def append_section() -> None:
            content = clean_text("\n".join(body_lines))
            if content:
                locator = f"heading:{heading}" if heading else "document"
                sections.append(
                    ParsedSection(
                        heading=heading,
                        locator=locator,
                        content=content,
                    )
                )

        for line in path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^#{1,6}\s+(.+?)\s*#*$", line)
            if match:
                append_section()
                heading = clean_text(match.group(1))
                body_lines = []
            else:
                body_lines.append(line)
        append_section()
        return tuple(sections)
