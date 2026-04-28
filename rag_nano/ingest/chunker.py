from __future__ import annotations

from pathlib import Path

CHUNK_SIZE_DEFAULT = 512
CHUNK_OVERLAP_DEFAULT = 64


def chunk_markdown(text: str, max_size: int = CHUNK_SIZE_DEFAULT) -> list[str]:
    chunks: list[str] = []
    heading_pattern = _HeadingPattern()
    lines = text.splitlines()
    current: list[str] = []
    current_size = 0

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            if current:
                _flush(current, chunks, max_size)
                current = []
            current_size = 0
        current.append(line)
        current_size += len(line) + 1
        if current_size >= max_size:
            _flush(current, chunks, max_size)
            current = []

    if current:
        _flush(current, chunks, max_size)
    return chunks if chunks else [text[:max_size]]


def chunk_code(text: str, window_size: int = CHUNK_SIZE_DEFAULT, overlap: int = CHUNK_OVERLAP_DEFAULT) -> list[str]:
    lines = text.splitlines()
    chunks: list[str] = []
    i = 0
    while i < len(lines):
        window = lines[i : i + window_size]
        chunks.append("\n".join(window))
        i += window_size - overlap
        if i >= len(lines):
            break
    return chunks


def _flush(lines: list[str], chunks: list[str], max_size: int) -> None:
    section = "\n".join(lines)
    if len(section) <= max_size:
        chunks.append(section)
    else:
        for j in range(0, len(section), max_size - 32):
            sub = section[j : j + max_size]
            if sub.strip():
                chunks.append(sub)


class _HeadingPattern:
    pass


def chunk(text: str, data_type: str, max_size: int = CHUNK_SIZE_DEFAULT) -> list[str]:
    if data_type in ("sop", "faq", "wiki", "document", "case_study", "issue_summary", "config_note", "knowledge_card"):
        return chunk_markdown(text, max_size)
    if data_type in ("code_summary",):
        return chunk_code(text, max_size, CHUNK_OVERLAP_DEFAULT)
    if data_type in ("log_summary",):
        return chunk_markdown(text, max_size)
    return chunk_markdown(text, max_size)
