"""Tests for the local embedding adapter without downloading a real model."""

from pathlib import Path

import numpy as np
import pytest

from app.core.config import Settings
from app.rag.embeddings import (
    BGE_ZH_QUERY_INSTRUCTION,
    SentenceTransformerEmbedder,
)


class FakeSentenceTransformer:
    """Small deterministic replacement that records encode arguments."""

    def __init__(self, dimension: int = 3) -> None:
        self.dimension = dimension
        self.calls: list[tuple[list[str], dict[str, object]]] = []

    def get_embedding_dimension(self) -> int:
        return self.dimension

    def encode(self, texts: list[str], **kwargs):
        self.calls.append((texts, kwargs))
        return np.array([[1.0, 0.0, 0.0] for _text in texts])


def _embedder(tmp_path: Path, fake: FakeSentenceTransformer):
    settings = Settings(
        _env_file=None,
        embedding_dimension=3,
        embedding_cache_dir=tmp_path,
        embedding_batch_size=4,
    )
    return SentenceTransformerEmbedder(
        settings,
        model_factory=lambda *_args, **_kwargs: fake,
    )


def test_document_embedding_uses_normalized_batch_encoding(tmp_path: Path) -> None:
    """Passages should not receive the query-only BGE instruction."""

    fake = FakeSentenceTransformer()
    embedder = _embedder(tmp_path, fake)

    vectors = embedder.embed_documents(["first", "second"])

    assert vectors == [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]]
    texts, options = fake.calls[0]
    assert texts == ["first", "second"]
    assert options["normalize_embeddings"] is True
    assert options["batch_size"] == 4


def test_query_embedding_adds_official_chinese_instruction(tmp_path: Path) -> None:
    """Short retrieval queries should use the BGE query prefix."""

    fake = FakeSentenceTransformer()
    embedder = _embedder(tmp_path, fake)

    embedder.embed_query("稻纵卷叶螟有什么危害")

    assert fake.calls[0][0] == [
        f"{BGE_ZH_QUERY_INSTRUCTION}稻纵卷叶螟有什么危害"
    ]


def test_blank_query_is_rejected(tmp_path: Path) -> None:
    """Whitespace must not be sent to the embedding model."""

    embedder = _embedder(tmp_path, FakeSentenceTransformer())

    with pytest.raises(ValueError, match="cannot be blank"):
        embedder.embed_query("   ")


def test_dimension_mismatch_fails_at_startup(tmp_path: Path) -> None:
    """Qdrant collection dimensions cannot silently differ from the model."""

    settings = Settings(
        _env_file=None,
        embedding_dimension=512,
        embedding_cache_dir=tmp_path,
    )
    with pytest.raises(ValueError, match="Expected embedding dimension 512"):
        SentenceTransformerEmbedder(
            settings,
            model_factory=lambda *_args, **_kwargs: FakeSentenceTransformer(3),
        )
