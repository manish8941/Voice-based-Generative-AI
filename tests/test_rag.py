"""
Unit Tests for Local RAG Engine
Verifies document chunking, inverted index construction, BM25 scoring, and query decomposition.
"""

import unittest
from src.rag_engine import LocalRAGEngine, DocumentChunk


class TestLocalRAGEngine(unittest.TestCase):

    def setUp(self):
        self.rag = LocalRAGEngine(top_k=2, chunk_size=50, overlap=10)

    def test_indexing_and_bm25_retrieval(self):
        doc1 = """
        # Authentication Service
        We use OAuth2 and JWT bearer tokens for secure user authentication.
        Tokens expire in 3600 seconds and are signed with RS256.
        """
        doc2 = """
        # Database Storage Layer
        PostgreSQL database with SQLAlchemy ORM models.
        Connection pooling with 10 max overflow connections.
        """
        self.rag.index_text(doc1, source_name="auth.md")
        self.rag.index_text(doc2, source_name="db.md")

        self.assertEqual(len(self.rag.chunks), 2)

        # Search for JWT Auth
        results = self.rag.search("JWT user authentication token", top_k=1)
        self.assertTrue(len(results) > 0)
        top_chunk, score = results[0]
        self.assertEqual(top_chunk.source_path, "auth.md")
        self.assertIn("OAuth2", top_chunk.content)

        # Search for Postgres Database
        results_db = self.rag.search("PostgreSQL SQLAlchemy connection", top_k=1)
        self.assertTrue(len(results_db) > 0)
        self.assertEqual(results_db[0][0].source_path, "db.md")

    def test_query_decomposition(self):
        transcript = (
            "We need to build a system that connects to our database schema "
            "and also implements an API endpoint for JWT authentication."
        )
        queries = self.rag.decompose_query(transcript)
        self.assertTrue(len(queries) >= 1)


if __name__ == "__main__":
    unittest.main()
