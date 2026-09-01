"""
RAG Engine (Retrieval-Augmented Generation) Module
Provides local document indexing, chunking, semantic keyword/BM25 retrieval, query decomposition,
and grounded context injection for spoken brain-dumps and technical specifications.
"""

import math
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class DocumentChunk:
    """Represents a chunk of indexed technical documentation or code."""

    def __init__(self, source_path: str, chunk_id: int, content: str, title: str = ""):
        self.source_path = source_path
        self.chunk_id = chunk_id
        self.content = content.strip()
        self.title = title or Path(source_path).name
        self.tokens: List[str] = self._tokenize(self.content)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Convert text into normalized lowercase alphanumeric tokens."""
        return re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", text.lower())


class LocalRAGEngine:
    """Lightweight, self-contained RAG and semantic retrieval engine."""

    def __init__(self, top_k: int = 4, chunk_size: int = 400, overlap: int = 50):
        self.top_k = top_k
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.chunks: List[DocumentChunk] = []
        self.doc_freqs: Dict[str, int] = {}
        self.total_docs: int = 0
        self.avg_doc_len: float = 0.0

    def clear(self):
        """Reset the index."""
        self.chunks = []
        self.doc_freqs = {}
        self.total_docs = 0
        self.avg_doc_len = 0.0

    def index_directory(self, dir_path: str, file_extensions: Optional[List[str]] = None) -> int:
        """Scan a directory and index all matching code and document files."""
        if file_extensions is None:
            file_extensions = [".md", ".py", ".txt", ".json", ".yaml", ".yml", ".ts", ".js", ".sql", ".rst"]

        indexed_files = 0
        path = Path(dir_path)
        if not path.exists():
            return 0

        for root, _, files in os.walk(path):
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in file_extensions:
                    full_path = os.path.join(root, file)
                    try:
                        self.index_file(full_path)
                        indexed_files += 1
                    except Exception:
                        continue

        self._recompute_bm25_stats()
        return indexed_files

    def index_text(self, text: str, source_name: str = "custom_context"):
        """Index raw text directly into chunks."""
        words = text.split()
        if not words:
            return

        chunk_id = 0
        step = max(1, self.chunk_size - self.overlap)
        for i in range(0, len(words), step):
            chunk_words = words[i : i + self.chunk_size]
            chunk_content = " ".join(chunk_words)
            if len(chunk_content.strip()) > 20:
                chunk = DocumentChunk(
                    source_path=source_name,
                    chunk_id=chunk_id,
                    content=chunk_content,
                    title=source_name,
                )
                self.chunks.append(chunk)
                chunk_id += 1

        self._recompute_bm25_stats()

    def index_file(self, file_path: str):
        """Chunk and index a single file."""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Handle Markdown sections or general code files
        if file_path.endswith(".md"):
            # Split by markdown headers
            sections = re.split(r"(?=(?:^|\n)#{1,3}\s)", content)
            chunk_id = 0
            for sec in sections:
                if len(sec.strip()) > 30:
                    chunk = DocumentChunk(
                        source_path=file_path,
                        chunk_id=chunk_id,
                        content=sec.strip(),
                        title=Path(file_path).name,
                    )
                    self.chunks.append(chunk)
                    chunk_id += 1
        else:
            # Fixed-window chunking
            lines = content.splitlines()
            line_chunk_size = 40
            line_overlap = 10
            step = max(1, line_chunk_size - line_overlap)
            chunk_id = 0
            for i in range(0, len(lines), step):
                chunk_lines = lines[i : i + line_chunk_size]
                chunk_text = "\n".join(chunk_lines)
                if len(chunk_text.strip()) > 20:
                    chunk = DocumentChunk(
                        source_path=file_path,
                        chunk_id=chunk_id,
                        content=chunk_text,
                        title=Path(file_path).name,
                    )
                    self.chunks.append(chunk)
                    chunk_id += 1

    def _recompute_bm25_stats(self):
        """Compute document frequencies and average document length for BM25 ranking."""
        self.doc_freqs = {}
        self.total_docs = len(self.chunks)
        if self.total_docs == 0:
            self.avg_doc_len = 0.0
            return

        total_tokens = 0
        for chunk in self.chunks:
            total_tokens += len(chunk.tokens)
            unique_tokens = set(chunk.tokens)
            for token in unique_tokens:
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1

        self.avg_doc_len = total_tokens / self.total_docs

    def _score_bm25(self, query_tokens: List[str], chunk: DocumentChunk, k1: float = 1.5, b: float = 0.75) -> float:
        """Calculate Okapi BM25 relevance score for a chunk given query tokens."""
        score = 0.0
        doc_len = len(chunk.tokens)
        if doc_len == 0 or self.total_docs == 0:
            return 0.0

        # Term frequencies in chunk
        tf_map: Dict[str, int] = {}
        for tok in chunk.tokens:
            tf_map[tok] = tf_map.get(tok, 0) + 1

        for q in query_tokens:
            if q not in tf_map:
                continue
            tf = tf_map[q]
            df = self.doc_freqs.get(q, 0)
            idf = math.log(1.0 + (self.total_docs - df + 0.5) / (df + 0.5))
            
            numerator = tf * (k1 + 1.0)
            denominator = tf + k1 * (1.0 - b + b * (doc_len / (self.avg_doc_len or 1.0)))
            score += idf * (numerator / denominator)

        return score

    def decompose_query(self, transcript: str) -> List[str]:
        """Decompose a free-form spoken transcript into focused technical search queries."""
        # Clean text
        clean_text = re.sub(r"[^\w\s\.\-]", " ", transcript)
        sentences = [s.strip() for s in re.split(r"[.\n]+", clean_text) if len(s.strip()) > 15]

        # Extract domain keywords
        keywords = re.findall(
            r"\b(?:api|database|auth|model|frontend|backend|framework|schema|workflow|test|deploy|docker|groq|whisper|llm|rag|ui|component|service|endpoint|token|state|react|python|fastapi|pyqt)\b",
            clean_text.lower(),
        )

        queries = []
        if keywords:
            queries.append(" ".join(list(set(keywords))))

        # Take up to 3 descriptive sentences
        for sentence in sentences[:3]:
            queries.append(sentence)

        if not queries:
            queries.append(transcript[:200])

        return queries

    def search(self, query: str, top_k: Optional[int] = None) -> List[Tuple[DocumentChunk, float]]:
        """Search indexed knowledge base for top matching chunks."""
        if not self.chunks:
            return []

        k = top_k or self.top_k
        query_tokens = DocumentChunk._tokenize(query)
        if not query_tokens:
            return []

        scored_chunks: List[Tuple[DocumentChunk, float]] = []
        for chunk in self.chunks:
            score = self._score_bm25(query_tokens, chunk)
            if score > 0.01:
                scored_chunks.append((chunk, score))

        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:k]

    def retrieve_grounded_context(self, transcript: str, top_k: Optional[int] = None) -> str:
        """Decomposes transcript, retrieves top matching context chunks, and formats them for prompt injection."""
        if not self.chunks:
            return ""

        queries = self.decompose_query(transcript)
        seen_chunks = set()
        matched_results: List[Tuple[DocumentChunk, float]] = []

        for q in queries:
            results = self.search(q, top_k=top_k or self.top_k)
            for chunk, score in results:
                identifier = f"{chunk.source_path}:{chunk.chunk_id}"
                if identifier not in seen_chunks:
                    seen_chunks.add(identifier)
                    matched_results.append((chunk, score))

        matched_results.sort(key=lambda x: x[1], reverse=True)
        top_matches = matched_results[: (top_k or self.top_k)]

        if not top_matches:
            return ""

        context_blocks = ["### Retrieved Project & Architecture Context (RAG):"]
        for chunk, score in top_matches:
            source_basename = Path(chunk.source_path).name
            context_blocks.append(
                f"**[Source: {source_basename} (Section {chunk.chunk_id})]**\n```\n{chunk.content}\n```"
            )

        return "\n\n".join(context_blocks)
