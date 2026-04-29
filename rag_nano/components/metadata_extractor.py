from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DefaultMetadataExtractor:
    def extract(self, source_path: str, content: str) -> dict[str, str]:
        meta: dict[str, str] = {}
        frontmatter = _parse_yaml_frontmatter(content)
        if frontmatter:
            meta.update(frontmatter)

        if "category" not in meta:
            meta["category"] = _derive_category(source_path)
        if "summary" not in meta:
            meta["summary"] = _extract_summary(content)[:500]
        if "data_type" not in meta:
            meta["data_type"] = _derive_data_type(source_path)

        return meta


class MockMetadataExtractor:
    def __init__(self, fixed: dict[str, str] | None = None) -> None:
        self.fixed = fixed or {}

    def extract(self, source_path: str, content: str) -> dict[str, str]:
        return dict(self.fixed)


def _parse_yaml_frontmatter(content: str) -> dict[str, str] | None:
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    fm = parts[1].strip()
    result: dict[str, str] = {}
    for line in fm.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            result[key.strip()] = val.strip().strip('"').strip("'")
    return result


def _derive_category(source_path: str) -> str:
    p = Path(source_path)
    if len(p.parts) >= 2:
        return p.parts[-2]
    return p.stem


def _derive_data_type(source_path: str) -> str:
    p = Path(source_path)
    suffix = p.suffix.lower()
    if suffix in (".md", ".markdown"):
        return "document"
    if suffix in (".py", ".js", ".ts", ".go", ".rs", ".java"):
        return "code_summary"
    return "document"


def _extract_summary(content: str) -> str:
    # Skip frontmatter
    text = content
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2]
    text = text.strip()

    # First non-empty line
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def get_metadata_extractor(_settings: Any) -> Any:
    return DefaultMetadataExtractor()
