"""Section-aware Markdown chunking for the seller warranty policy corpus."""

from __future__ import annotations

import re
from pathlib import Path

from .chunking import RecursiveChunker
from .models import Document


HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def read_policy(path: Path) -> tuple[dict[str, str], str]:
    """Read the corpus's simple YAML-like metadata header and Markdown body."""
    raw = path.read_text(encoding="utf-8-sig")
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"Missing metadata header: {path}")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration as exc:
        raise ValueError(f"Unclosed metadata header: {path}") from exc
    metadata = {}
    for line in lines[1:end]:
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()
    required = {"doc_id", "title", "source_url", "retrieved_at", "document_version", "audience", "category", "language"}
    missing = required - metadata.keys()
    if missing:
        raise ValueError(f"Missing metadata {sorted(missing)}: {path}")
    if metadata["doc_id"] != path.stem:
        raise ValueError(f"doc_id differs from filename: {path}")
    return metadata, "\n".join(lines[end + 1:]).strip()


def chunk_policy(path: Path, max_chars: int = 1200) -> list[Document]:
    """Split at Markdown headings, then split oversized sections within their heading path."""
    if max_chars < 100:
        raise ValueError("max_chars must be at least 100")
    base_metadata, body = read_policy(path)
    sections: list[tuple[list[str], int, list[str]]] = []
    stack: list[str] = []
    current: list[str] = []
    current_level = 0

    def flush() -> None:
        content = "\n".join(current).strip()
        if content:
            sections.append((list(stack), current_level, list(current)))

    for line in body.splitlines():
        match = HEADING.match(line)
        if match:
            flush()
            level, title = len(match.group(1)), match.group(2).strip()
            stack = stack[:level - 1] + [title]
            current_level = level
            current = []
        else:
            current.append(line)
    flush()

    output: list[Document] = []
    for path_parts, level, lines in sections:
        section_text = "\n".join(lines).strip()
        heading_path = " > ".join(path_parts) if path_parts else base_metadata["title"]
        prefix = f"{heading_path}\n\n"
        budget = max_chars - len(prefix)
        if budget < 50:
            raise ValueError(f"Heading path exceeds chunk budget: {heading_path}")
        pieces = ([section_text] if len(section_text) <= budget
                  else RecursiveChunker(chunk_size=budget).chunk(section_text))
        for index, piece in enumerate(pieces):
            metadata = {
                **base_metadata,
                "source_file": path.as_posix(),
                "heading_path": heading_path,
                "heading_level": level,
                "section_part": index + 1,
                "section_parts": len(pieces),
                "split_method": "heading" if len(pieces) == 1 else "heading+recursive",
            }
            output.append(Document(
                id=f"{path.stem}#{len(output)}",
                content=prefix + piece,
                metadata=metadata,
            ))
    return output


def chunk_corpus(directory: Path, max_chars: int = 1200) -> list[Document]:
    return [chunk for path in sorted(directory.glob("*.md")) for chunk in chunk_policy(path, max_chars)]
