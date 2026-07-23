"""Framework-independent text embedding interface and local BGE adapter."""

from collections.abc import Callable, Sequence
from typing import Any, Protocol

from app.core.config import PROJECT_ROOT, Settings

BGE_ZH_QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："


class TextEmbedder(Protocol):
    """Behavior required by indexing and retrieval services."""

    @property
    def dimension(self) -> int:
        """Return the fixed vector length produced by the model."""

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed source passages without a query instruction."""

    def embed_query(self, text: str) -> list[float]:
        """Embed one short retrieval query."""


class SentenceTransformerEmbedder:
    """Run BGE locally with normalized vectors and query-only instruction."""

    def __init__(
        self,
        settings: Settings,
        *,
        model_factory: Callable[..., Any] | None = None,
    ) -> None:
        if model_factory is None:
            from sentence_transformers import SentenceTransformer

            model_factory = SentenceTransformer

        cache_dir = settings.embedding_cache_dir
        if not cache_dir.is_absolute():
            cache_dir = PROJECT_ROOT / cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._model = model_factory(
            settings.embedding_model,
            device=settings.embedding_device,
            cache_folder=str(cache_dir),
            trust_remote_code=False,
        )
        dimension = self._model.get_embedding_dimension()
        if dimension != settings.embedding_dimension:
            raise ValueError(
                f"Expected embedding dimension {settings.embedding_dimension}, "
                f"got {dimension}."
            )
        self._dimension = settings.embedding_dimension
        self._batch_size = settings.embedding_batch_size

    @property
    def dimension(self) -> int:
        """Return the dimension verified when the model was loaded."""

        return self._dimension

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Encode passages as unit-length vectors suitable for cosine search."""

        if not texts:
            return []
        return self._encode(list(texts))

    def embed_query(self, text: str) -> list[float]:
        """Prefix the official Chinese retrieval instruction before encoding."""

        clean_text = text.strip()
        if not clean_text:
            raise ValueError("A retrieval query cannot be blank.")
        return self._encode([f"{BGE_ZH_QUERY_INSTRUCTION}{clean_text}"])[0]

    def _encode(self, texts: list[str]) -> list[list[float]]:
        """Convert the model's array output to JSON-safe Python floats."""

        vectors = self._model.encode(
            texts,
            batch_size=self._batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return [
            [float(value) for value in vector]
            for vector in vectors.tolist()
        ]
