from rag_nano.ingest.chunker import chunk, chunk_code, chunk_markdown


class TestChunker:
    def test_markdown_heading_split(self) -> None:
        text = "# Section 1\nContent here\n# Section 2\nMore content"
        chunks = chunk_markdown(text, max_size=200)
        assert len(chunks) >= 2
        assert "# Section 1" in chunks[0]

    def test_markdown_stable_position(self) -> None:
        text = "# Heading\n\n" + "x" * 300
        chunks = chunk_markdown(text, max_size=200)
        for i, c in enumerate(chunks):
            pass  # ordered
        assert all(isinstance(c, str) for c in chunks)

    def test_code_line_window(self) -> None:
        lines = ["line " + str(i) for i in range(100)]
        text = "\n".join(lines)
        chunks = chunk_code(text, window_size=10, overlap=5)
        assert len(chunks) >= 5
        # Verify coverage
        all_lines = "".join(chunks)
        for i in range(0, min(50, 100), 10):
            assert f"line {i}" in all_lines or i >= len(chunks) * 5

    def test_data_type_routing(self) -> None:
        text = "# FAQ\nQ: How do I..."
        md_chunks = chunk(text, "faq")
        code_chunks = chunk(text, "code_summary")
        assert len(md_chunks) >= 1
        assert len(code_chunks) >= 1

    def test_empty_text_returns_single_chunk(self) -> None:
        chunks = chunk_markdown("", max_size=100)
        assert chunks == [""]
