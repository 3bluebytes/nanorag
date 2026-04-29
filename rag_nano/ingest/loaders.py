from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

CONTENT_SIZE_LIMIT = 5 * 1024 * 1024
CHUNK_SIZE_DEFAULT = 512
CHUNK_OVERLAP_DEFAULT = 64


SUPPORTED_EXTENSIONS = {
    ".md",
    ".markdown",
    ".txt",
    ".py",
    ".js",
    ".ts",
    ".go",
    ".rs",
    ".java",
    ".sh",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".log",
}


def _load_markdown(path: Path, text: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    meta[key.strip()] = val.strip().strip('"').strip("'")
    return meta


def _load_code(path: Path, text: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    comment_block = ""
    for line in text.splitlines()[:50]:
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("/*"):
            comment_block += stripped.lstrip("#/").strip() + "\n"
        elif stripped:
            break
    if comment_block.strip():
        meta["summary"] = comment_block.strip()[:500]
    return meta


_LOADERS: dict[str, Callable[[Path, str], dict[str, str]]] = {
    ".md": _load_markdown,
    ".markdown": _load_markdown,
    ".py": _load_code,
    ".js": _load_code,
    ".ts": _load_code,
    ".go": _load_code,
    ".rs": _load_code,
    ".java": _load_code,
}


@dataclass
class RawItem:
    source_path: str
    content: str
    original_metadata: dict[str, str]


@dataclass
class LoaderResult:
    item: RawItem | None
    rejection_reason: str | None


def load_file(path: Path) -> LoaderResult:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        return LoaderResult(item=None, rejection_reason="unsupported_format")

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            content = path.read_text(encoding="latin-1")
        except Exception:
            return LoaderResult(item=None, rejection_reason="unsupported_format")

    if not content.strip():
        return LoaderResult(item=None, rejection_reason="cold_data_raw_dump")

    meta: dict[str, str] = {}
    loader = _LOADERS.get(suffix)
    if loader:
        meta = loader(path, content)

    return LoaderResult(
        item=RawItem(
            source_path=str(path),
            content=content,
            original_metadata=meta,
        ),
        rejection_reason=None,
    )
