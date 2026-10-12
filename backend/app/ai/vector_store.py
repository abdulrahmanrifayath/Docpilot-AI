import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.config import settings
from app.ai.embeddings import embedding_service


class VectorChunk(BaseModel):
    id: str
    repository_id: str
    chunk_type: str  # code, doc, api, model
    title: str
    file_path: str
    start_line: int = 1
    end_line: int = 1
    content: str
    vector: List[float] = Field(default_factory=list)


class SearchResult(BaseModel):
    chunk: VectorChunk
    score: float


class VectorStore:
    def __init__(self) -> None:
        self.storage_dir = settings.VECTOR_STORE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._indices: Dict[str, List[VectorChunk]] = {}

    def _index_file(self, repository_id: str) -> Path:
        return self.storage_dir / f"{repository_id}.json"

    def add_chunks(self, repository_id: str, chunks: List[VectorChunk]) -> None:
        if repository_id not in self._indices:
            self._indices[repository_id] = []
        self._indices[repository_id].extend(chunks)
        self.save_index(repository_id)

    def clear(self, repository_id: str) -> None:
        self._indices[repository_id] = []
        idx_file = self._index_file(repository_id)
        if idx_file.exists():
            idx_file.unlink()

    def save_index(self, repository_id: str) -> None:
        chunks = self._indices.get(repository_id, [])
        idx_file = self._index_file(repository_id)
        data = [chunk.model_dump() for chunk in chunks]
        idx_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load_index(self, repository_id: str) -> List[VectorChunk]:
        if repository_id in self._indices and self._indices[repository_id]:
            return self._indices[repository_id]

        idx_file = self._index_file(repository_id)
        if not idx_file.exists():
            self._indices[repository_id] = []
            return []

        try:
            data = json.loads(idx_file.read_text(encoding="utf-8"))
            chunks = [VectorChunk(**item) for item in data]
            self._indices[repository_id] = chunks
            return chunks
        except Exception:
            self._indices[repository_id] = []
            return []

    async def search(self, query: str, repository_id: str, top_k: int = 5) -> List[SearchResult]:
        chunks = self.load_index(repository_id)
        if not chunks:
            return []

        query_vector = await embedding_service.get_embedding(query)
        results: List[SearchResult] = []

        for chunk in chunks:
            if not chunk.vector:
                continue
            sim = embedding_service.similarity(query_vector, chunk.vector)
            results.append(SearchResult(chunk=chunk, score=sim))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]


vector_store = VectorStore()
