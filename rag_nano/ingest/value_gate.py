from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rag_nano.types import DataType

if TYPE_CHECKING:
    from rag_nano.ingest.loaders import RawItem

logger = logging.getLogger(__name__)

MAX_RAW_CONVERSATION_SIZE = 500 * 1024

COLD_DATA_PATTERNS = [
    (re.compile(r"^\d{4}-\d{2}-\d{2}[T\s].*(?:INFO|WARN|ERROR|DEBUG)", re.M), "cold_data_raw_log"),
    (re.compile(r"^\d{4}-\d{2}-\d{2}.*\d{2}:\d{2}:\d{2}", re.M), "cold_data_raw_log"),
    (re.compile(r"(?:stack\s*trace|exception\s*in|at\s+\w+\.\w+\()", re.I), "cold_data_raw_trace"),
    (re.compile(r"^\s*\{.*['\"][^'\"]*['\"]\s*:.*\}\s*$", re.M), "cold_data_raw_dump"),
]


def _looks_like_conversation(text: str) -> bool:
    lines = text.splitlines()[:50]
    user_count = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("user:", "human:", "> ")):
            user_count += 1
    return user_count >= 3


def classify_data_type(item: RawItem) -> DataType:
    if item.original_metadata.get("data_type"):
        try:
            return DataType(item.original_metadata["data_type"])
        except ValueError:
            pass
    p = Path(item.source_path)
    suffix = p.suffix.lower()
    if suffix in (".py", ".js", ".ts", ".go", ".rs", ".java"):
        return DataType.code_summary
    if suffix in (".md", ".markdown"):
        # Check parent directory first, then filename stem
        parts = p.parts
        for part in parts:
            part_lower = part.lower()
            if "faq" in part_lower:
                return DataType.faq
            if "sop" in part_lower or "standard" in part_lower or "procedure" in part_lower:
                return DataType.sop
            if "wiki" in part_lower:
                return DataType.wiki
    return DataType.document


def check_cold_data(item: RawItem) -> str | None:
    text = item.content
    if len(text) > MAX_RAW_CONVERSATION_SIZE and _looks_like_conversation(text):
        return "cold_data_oversized_conversation"
    for pattern, reason in COLD_DATA_PATTERNS:
        if pattern.search(text):
            return reason
    return None


def check_duplicate(structured_store: Any, item: RawItem) -> str | None:
    content_hash = hashlib.sha256(item.content.encode()).hexdigest()
    existing = structured_store.get_source_by_path_and_hash(item.source_path, content_hash)
    if existing:
        return "cold_data_duplicate"
    return None


def evaluate(
    item: RawItem,
    structured_store: Any,
    override_data_type: DataType | None = None,
) -> tuple[DataType, str | None]:
    data_type = override_data_type or classify_data_type(item)

    cold = check_cold_data(item)
    if cold:
        return data_type, cold

    dup = check_duplicate(structured_store, item)
    if dup:
        return data_type, dup

    return data_type, None
