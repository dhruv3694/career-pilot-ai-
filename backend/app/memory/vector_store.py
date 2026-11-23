"""
Local Vector Store and Semantic Evidence Retrieval Service.
Implements local document chunking, indexing, and retrieval with lexical and vector cosine similarity.
Runs completely offline without paid API requirements.
"""

from __future__ import annotations

import logging
import math
import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DocumentChunk(BaseModel):
    """A searchable chunk of text with metadata."""
    chunk_id: str
    doc_id: str
    doc_type: str  # resume, job_description, learning_resource
    title: str
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tokens: List[str] = Field(default_factory=list)


class SearchResult(BaseModel):
    """Retrieval search match with evidence score."""
    chunk_id: str
    doc_id: str
    doc_type: str
    title: str
    text: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


def _tokenize(text: str) -> List[str]:
    """Tokenize and normalize text."""
    return [w.lower() for w in re.findall(r"[a-zA-Z0-9_+#.]+", text) if len(w) > 1]


class LocalEvidenceVectorStore:
    """In-memory local vector and lexical retrieval index."""

    def __init__(self):
        self.chunks: Dict[str, DocumentChunk] = {}
        self.idf_cache: Dict[str, float] = {}

    def index_document(
        self,
        doc_id: str,
        doc_type: str,
        title: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 400,
    ) -> List[str]:
        """Split text into chunks and index them."""
        metadata = metadata or {}
        words = text.split()
        created_chunk_ids = []

        if not words:
            return created_chunk_ids

        step = max(100, chunk_size - 100)
        idx = 0
        for i in range(0, len(words), step):
            chunk_words = words[i : i + chunk_size]
            chunk_text = " ".join(chunk_words)
            chunk_id = f"{doc_id}_{idx}"
            tokens = _tokenize(chunk_text)

            chunk = DocumentChunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                doc_type=doc_type,
                title=title,
                text=chunk_text,
                metadata=metadata,
                tokens=tokens,
            )
            self.chunks[chunk_id] = chunk
            created_chunk_ids.append(chunk_id)
            idx += 1

        self._recompute_idf()
        return created_chunk_ids

    def _recompute_idf(self):
        """Update inverse document frequency across chunks."""
        total_docs = len(self.chunks)
        if total_docs == 0:
            return

        doc_freq: Dict[str, int] = {}
        for chunk in self.chunks.values():
            unique_terms = set(chunk.tokens)
            for term in unique_terms:
                doc_freq[term] = doc_freq.get(term, 0) + 1

        self.idf_cache = {
            term: math.log((total_docs + 1) / (df + 1)) + 1.0
            for term, df in doc_freq.items()
        }

    def search(
        self,
        query: str,
        doc_type: Optional[str] = None,
        top_k: int = 5,
        min_score: float = 0.05,
    ) -> List[SearchResult]:
        """Search indexed chunks using TF-IDF cosine similarity."""
        query_tokens = _tokenize(query)
        if not query_tokens or not self.chunks:
            return []

        # Query vector
        query_tf: Dict[str, int] = {}
        for t in query_tokens:
            query_tf[t] = query_tf.get(t, 0) + 1

        query_vec: Dict[str, float] = {}
        query_norm = 0.0
        for t, tf in query_tf.items():
            idf = self.idf_cache.get(t, 1.0)
            weight = tf * idf
            query_vec[t] = weight
            query_norm += weight * weight
        query_norm = math.sqrt(query_norm) if query_norm > 0 else 1.0

        results: List[SearchResult] = []

        for chunk in self.chunks.values():
            if doc_type and chunk.doc_type != doc_type:
                continue

            # Chunk vector
            chunk_tf: Dict[str, int] = {}
            for t in chunk.tokens:
                chunk_tf[t] = chunk_tf.get(t, 0) + 1

            chunk_norm = 0.0
            dot_product = 0.0
            for t, tf in chunk_tf.items():
                idf = self.idf_cache.get(t, 1.0)
                weight = tf * idf
                chunk_norm += weight * weight
                if t in query_vec:
                    dot_product += weight * query_vec[t]

            chunk_norm = math.sqrt(chunk_norm) if chunk_norm > 0 else 1.0
            score = dot_product / (query_norm * chunk_norm)

            if score >= min_score:
                results.append(
                    SearchResult(
                        chunk_id=chunk.chunk_id,
                        doc_id=chunk.doc_id,
                        doc_type=chunk.doc_type,
                        title=chunk.title,
                        text=chunk.text,
                        score=round(score, 4),
                        metadata=chunk.metadata,
                    )
                )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def delete_document(self, doc_id: str) -> int:
        """Delete all chunks for a document."""
        to_del = [cid for cid, chunk in self.chunks.items() if chunk.doc_id == doc_id]
        for cid in to_del:
            del self.chunks[cid]
        self._recompute_idf()
        return len(to_del)


vector_store = LocalEvidenceVectorStore()

