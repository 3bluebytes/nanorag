"""Chunking utilities for the ingest pipeline."""


def chunk_markdown(text: str, max_size: int = 512) -> list[str]:
    """Split markdown by headings, then recursively split large sections."""
    chunks = []
    for section in split_by_heading(text):
        if len(section) <= max_size:
            chunks.append(section)
        else:
            chunks.extend(split_by_chars(section, max_size))
    return chunks
