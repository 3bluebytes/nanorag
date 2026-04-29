from unittest.mock import MagicMock, patch

import numpy as np

from rag_nano.components.embedding import (
    LocalSentenceTransformerProvider,
    MockEmbeddingProvider,
)


class TestLocalSentenceTransformerProvider:
    def test_prefix_convention_query(self) -> None:
        with patch("sentence_transformers.SentenceTransformer") as mock_cls:
            mock_model = MagicMock()
            mock_model.encode.return_value = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
            mock_cls.return_value = mock_model

            provider = LocalSentenceTransformerProvider("dummy-model")
            provider.encode(["hello world"], task="query")

            passed_texts = mock_model.encode.call_args[0][0]
            assert passed_texts[0].startswith("query: ")
            assert "hello world" in passed_texts[0]

    def test_prefix_convention_passage(self) -> None:
        with patch("sentence_transformers.SentenceTransformer") as mock_cls:
            mock_model = MagicMock()
            mock_model.encode.return_value = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
            mock_cls.return_value = mock_model

            provider = LocalSentenceTransformerProvider("dummy-model")
            provider.encode(["hello world"], task="passage")

            passed_texts = mock_model.encode.call_args[0][0]
            assert passed_texts[0].startswith("passage: ")
            assert "hello world" in passed_texts[0]


class TestMockEmbeddingProvider:
    def test_deterministic(self) -> None:
        provider = MockEmbeddingProvider(dim=8)
        e1 = provider.encode(["alpha", "beta"])
        e2 = provider.encode(["alpha", "beta"])
        np.testing.assert_array_equal(e1, e2)

    def test_dim_stable(self) -> None:
        provider = MockEmbeddingProvider(dim=128)
        e = provider.encode(["x"])
        assert e.shape == (1, 128)

    def test_l2_normalized(self) -> None:
        provider = MockEmbeddingProvider(dim=4)
        e = provider.encode(["a", "b", "c"])
        norms = np.linalg.norm(e, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-6)
