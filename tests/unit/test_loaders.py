from pathlib import Path

from rag_nano.ingest.loaders import load_file


class TestLoaders:
    def test_supported_markdown(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("---\ncategory: ops\n---\n# Title\nbody", encoding="utf-8")
        result = load_file(f)
        assert result.item is not None
        assert result.item.source_path == str(f)
        assert "category" in result.item.original_metadata

    def test_supported_code(self, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text('"""Docstring."""\nprint(1)', encoding="utf-8")
        result = load_file(f)
        assert result.item is not None
        assert "summary" in result.item.original_metadata or result.item.original_metadata == {}

    def test_unsupported_format(self, tmp_path: Path) -> None:
        f = tmp_path / "test.xyz"
        f.write_text("content", encoding="utf-8")
        result = load_file(f)
        assert result.item is None
        assert result.rejection_reason == "unsupported_format"

    def test_empty_file_rejected(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.md"
        f.write_text("   \n\n  ", encoding="utf-8")
        result = load_file(f)
        assert result.item is None
        assert result.rejection_reason == "cold_data_raw_dump"
