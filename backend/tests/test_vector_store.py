"""
backend/tests/test_vector_store.py

PURPOSE:
Unit tests verifying vector embedding generation and similarity search functions.

EXECUTION:
    PYTHONPATH=. python -m pytest backend/tests/test_vector_store.py
"""

from backend.app.rag.vector_store import VectorStoreManager, DocumentChunk

def test_embedding_generation():
    manager = VectorStoreManager(db_connection_url=None)
    text = "Patient diagnosed with Type 2 Diabetes Mellitus."
    
    embedding = manager.generate_embedding(text)
    
    assert isinstance(embedding, list)
    assert len(embedding) == VectorStoreManager.VECTOR_DIMENSION

def test_mock_similarity_search():
    manager = VectorStoreManager(db_connection_url=None)
    query = "Diabetes clinical trials"
    
    results = manager.similarity_search(query, limit=2)
    
    assert len(results) > 0
    assert results[0].score > 0.0
    assert "trial-NCT001" in results[0].chunk_id