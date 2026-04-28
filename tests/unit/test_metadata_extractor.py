from rag_nano.components.metadata_extractor import DefaultMetadataExtractor


class TestDefaultMetadataExtractor:
    def test_yaml_frontmatter_parsing(self) -> None:
        content = "---\ncategory: ops\nauthor: team\n---\n# Title\nbody"
        meta = DefaultMetadataExtractor().extract("test.md", content)
        assert meta["category"] == "ops"
        assert meta["author"] == "team"

    def test_category_fallback_to_parent_dir(self) -> None:
        meta = DefaultMetadataExtractor().extract("knowledge/faq/hello.md", "plain text")
        assert meta["category"] == "faq"

    def test_category_fallback_to_filename(self) -> None:
        meta = DefaultMetadataExtractor().extract("hello.md", "plain text")
        assert meta["category"] == "hello"

    def test_summary_fallback_to_first_line(self) -> None:
        meta = DefaultMetadataExtractor().extract("a.md", "First meaningful line\n\nrest")
        assert meta["summary"] == "First meaningful line"

    def test_data_type_from_extension(self) -> None:
        meta = DefaultMetadataExtractor().extract("script.py", "print(1)")
        assert meta["data_type"] == "code_summary"
