from functools import lru_cache
from math import sqrt

from fastembed import TextEmbedding

from src.core.config import settings


@lru_cache(maxsize=1)
def get_embedder() -> TextEmbedding:
    return TextEmbedding(model_name=settings.embedding_model_name)


def embed_texts(texts: list[str]) -> list[list[float]]:
    vectors = []
    for vector in get_embedder().embed(texts):
        values = vector.tolist()
        norm = sqrt(sum(value * value for value in values))
        if norm > 0:
            values = [value / norm for value in values]
        vectors.append(values)
    return vectors
