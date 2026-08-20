"""Optional embedding providers with a dependency-free command boundary."""

from __future__ import annotations

import hashlib
import json
import math
import shlex
import subprocess
from dataclasses import dataclass
from typing import Any, Protocol, Sequence


class EmbeddingProvider(Protocol):
    name: str
    dimension: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        ...


@dataclass
class HashEmbeddingProvider:
    """Deterministic local fallback; useful for tests, not semantic quality."""

    dimension: int = 256
    name: str = "hash"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if self.dimension < 8:
            raise ValueError("embedding dimension must be at least 8")
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self.dimension
            tokens = text.lower().split()
            for token in tokens:
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                index = int.from_bytes(digest[:4], "big") % self.dimension
                sign = 1.0 if digest[4] & 1 else -1.0
                vector[index] += sign
            norm = math.sqrt(sum(value * value for value in vector))
            if not norm:
                vector[0] = 1.0
                norm = 1.0
            vectors.append([value / norm for value in vector])
        return vectors


@dataclass
class CommandEmbeddingProvider:
    """Invoke a harness/local embedding adapter with JSON on stdin/stdout.

    Request: ``{"texts": ["..."]}``; response: ``{"embeddings": [[...]]}``.
    The command is argv-split and never executed through a shell.
    """

    command: Sequence[str]
    dimension: int
    timeout: int = 120
    name: str = "command"

    @classmethod
    def from_string(cls, command: str, dimension: int, timeout: int = 120) -> "CommandEmbeddingProvider":
        return cls(shlex.split(command), dimension, timeout)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not self.command:
            raise ValueError("embedding command is empty")
        result = subprocess.run(
            list(self.command),
            input=json.dumps({"texts": list(texts)}),
            text=True,
            capture_output=True,
            timeout=self.timeout,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(f"embedding command failed with exit code {result.returncode}")
        try:
            payload = json.loads(result.stdout)
            vectors = payload["embeddings"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ValueError("embedding command returned invalid JSON contract") from exc
        if len(vectors) != len(texts) or any(len(vector) != self.dimension for vector in vectors):
            raise ValueError("embedding command returned wrong batch size or dimension")
        return [[float(value) for value in vector] for vector in vectors]


class SentenceTransformerProvider:
    """Lazy local provider; requires the optional sentence-transformers package."""

    name = "sentence-transformers"

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError("local embeddings require optional dependency 'sentence-transformers'") from exc
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        self.dimension = int(self._model.get_sentence_embedding_dimension())

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [list(map(float, vector)) for vector in self._model.encode(list(texts), normalize_embeddings=True)]


def embedding_metadata(provider: EmbeddingProvider) -> dict[str, Any]:
    metadata = {"provider": provider.name, "dimension": provider.dimension}
    model_name = getattr(provider, "model_name", None)
    if model_name:
        metadata["model_name"] = str(model_name)
    return metadata
