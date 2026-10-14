import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict, AliasChoices

from app.core.config import settings
from app.ai.embeddings import embedding_service


class VectorChunk(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    project_id: str = Field(..., validation_alias=AliasChoices("project_id", "repository_id"))
    chunk_type: str = "code"  # file, class, function, api, model, doc, sequence, code
    title: str
    file_path: str
    start_line: int = 1
    end_line: int = 1
    content: str
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    vector: List[float] = Field(default_factory=list)

    @property
    def repository_id(self) -> str:
        return self.project_id


class SearchResult(BaseModel):
    chunk: VectorChunk
    score: float


class VectorStore:
    def __init__(self) -> None:
        self.storage_dir = settings.VECTOR_STORE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._indices: Dict[str, List[VectorChunk]] = {}

    def _index_file(self, project_id: str) -> Path:
        return self.storage_dir / f"{project_id}.json"

    def add_chunks(self, project_id: str, chunks: List[VectorChunk]) -> None:
        if project_id not in self._indices:
            self._indices[project_id] = []
        self._indices[project_id].extend(chunks)
        self.save_index(project_id)

    def clear(self, project_id: str) -> None:
        self._indices[project_id] = []
        idx_file = self._index_file(project_id)
        if idx_file.exists():
            try:
                idx_file.unlink()
            except OSError:
                pass

    def save_index(self, project_id: str) -> None:
        chunks = self._indices.get(project_id, [])
        idx_file = self._index_file(project_id)
        data = [chunk.model_dump() for chunk in chunks]
        idx_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load_index(self, project_id: str) -> List[VectorChunk]:
        if project_id in self._indices and self._indices[project_id]:
            return self._indices[project_id]

        idx_file = self._index_file(project_id)
        if not idx_file.exists():
            self._indices[project_id] = []
            return []

        try:
            data = json.loads(idx_file.read_text(encoding="utf-8"))
            chunks = [VectorChunk(**item) for item in data]
            self._indices[project_id] = chunks
            return chunks
        except Exception:
            self._indices[project_id] = []
            return []

    async def search(
        self,
        query: str,
        project_id: str,
        top_k: int = 6,
        chunk_types: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        """
        Searches repository-specific vectors with strict project_id isolation.
        No cross-project data is ever loaded or returned.
        """
        chunks = self.load_index(project_id)
        if not chunks:
            return []

        # Filter by chunk_types if specified
        if chunk_types:
            allowed = {t.lower() for t in chunk_types}
            candidate_chunks = [c for c in chunks if c.chunk_type.lower() in allowed]
        else:
            candidate_chunks = chunks

        if not candidate_chunks:
            return []

        query_vector = await embedding_service.get_embedding(query)
        results: List[SearchResult] = []

        for chunk in candidate_chunks:
            if not chunk.vector:
                continue
            sim = embedding_service.similarity(query_vector, chunk.vector)
            results.append(SearchResult(chunk=chunk, score=sim))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]


vector_store = VectorStore()

