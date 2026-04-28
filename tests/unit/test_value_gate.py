from unittest.mock import MagicMock

import pytest

from rag_nano.ingest.loaders import RawItem
from rag_nano.ingest.value_gate import check_cold_data, classify_data_type, evaluate


class TestClassifyDataType:
    def test_frontmatter_data_type(self) -> None:
        item = RawItem(source_path="docs/test.md", content="# Test", original_metadata={"data_type": "faq"})
        assert classify_data_type(item) == "faq"

    def test_filename_faq(self) -> None:
        item = RawItem(source_path="faq/test.md", content="plain", original_metadata={})
        assert classify_data_type(item) == "faq"

    def test_filename_sop(self) -> None:
        item = RawItem(source_path="sop/test.md", content="plain", original_metadata={})
        assert classify_data_type(item) == "sop"

    def test_filename_wiki(self) -> None:
        item = RawItem(source_path="wiki/test.md", content="plain", original_metadata={})
        assert classify_data_type(item) == "wiki"

    def test_code_extension(self) -> None:
        item = RawItem(source_path="test.py", content="print(1)", original_metadata={})
        assert classify_data_type(item) == "code_summary"

    def test_fallback_document(self) -> None:
        item = RawItem(source_path="readme.md", content="plain", original_metadata={})
        assert classify_data_type(item) == "document"


class TestCheckColdData:
    def test_raw_log_rejected(self) -> None:
        item = RawItem(source_path="a.log", content="2026-04-27T10:00:01Z INFO server started", original_metadata={})
        assert check_cold_data(item) == "cold_data_raw_log"

    def test_valid_document_accepted(self) -> None:
        item = RawItem(source_path="doc.md", content="# How to deploy\n\nFollow these steps...", original_metadata={})
        assert check_cold_data(item) is None


class TestValueGate:
    def test_all_data_types_accepted(self) -> None:
        from rag_nano.types import DataType
        store = MagicMock()
        store.get_source_by_path_and_hash.return_value = None  # not a duplicate
        for dtype in DataType:
            item = RawItem(source_path="doc.md", content="meaningful content", original_metadata={"data_type": dtype.value})
            dt, reason = evaluate(item, store)
            assert dt == dtype
            assert reason is None

    def test_cold_data_rejected(self) -> None:
        from rag_nano.types import DataType
        store = MagicMock()
        item = RawItem(source_path="server.log", content="2026-04-27T10:00:01Z INFO server started", original_metadata={})
        dt, reason = evaluate(item, store)
        assert reason == "cold_data_raw_log"

    def test_duplicate_rejected(self) -> None:
        from rag_nano.types import DataType
        store = MagicMock()
        store.get_source_by_path_and_hash.return_value = MagicMock()  # duplicate found
        item = RawItem(source_path="doc.md", content="meaningful content", original_metadata={})
        dt, reason = evaluate(item, store)
        assert reason == "cold_data_duplicate"
