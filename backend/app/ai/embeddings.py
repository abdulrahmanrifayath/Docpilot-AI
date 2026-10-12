import math
import re
from collections import Counter
from typing import Dict, List, Optional
import httpx

from app.core.config import settings


class LocalTFIDFVectorizer:
    """Lightweight vectorizer using term frequency and subword token hashing."""

    def __init__(self, vector_dim: int = 256) -> None:
        self.vector_dim = vector_dim

    def tokenize(self, text: str) -> List[str]:
        # Tokenize by word boundary and camelCase/snake_case
        tokens = re.findall(r"[A-Za-z0-9]+", text.lower())
        subwords = []
        for t in tokens:
            subwords.append(t)
            # Add character tri-grams for fuzzy code matching
            if len(t) >= 4:
                for i in range(len(t) - 2):
                    subwords.append(t[i : i + 3])
        return subwords

    def embed(self, text: str) -> List[float]:
        tokens = self.tokenize(text)
        if not tokens:
            return [0.0] * self.vector_dim

        counts = Counter(tokens)
        vector = [0.0] * self.vector_dim

        for token, count in counts.items():
            # Hash token into bucket
            bucket = abs(hash(token)) % self.vector_dim
            # TF weighting
            vector[bucket] += 1.0 + math.log(count)

        # L2 normalize vector
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        if len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        return max(0.0, min(1.0, dot))


class EmbeddingService:
    def __init__(self) -> None:
        self.provider = settings.EMBEDDING_PROVIDER
        self.local_vectorizer = LocalTFIDFVectorizer(vector_dim=256)

    async def get_embedding(self, text: str) -> List[float]:
        # If OpenAI key configured, attempt OpenAI embedding
        if settings.LLM_API_KEY and self.provider == "openai":
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.LLM_API_KEY}",
                }
                payload = {
                    "model": settings.EMBEDDING_MODEL,
                    "input": text[:8000],
                }
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        f"{settings.LLM_BASE_URL.rstrip('/')}/embeddings",
                        headers=headers,
                        json=payload,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        return data["data"][0]["embedding"]
            except Exception:
                pass

        # Fallback to local vectorizer
        return self.local_vectorizer.embed(text)

    def similarity(self, v1: List[float], v2: List[float]) -> float:
        return LocalTFIDFVectorizer.cosine_similarity(v1, v2)


embedding_service = EmbeddingService()
