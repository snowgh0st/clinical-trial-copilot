"""
backend/tests/test_ner.py

PURPOSE:
Unit tests for `BioBERTEntityExtractor` verifying clinical entity extraction from sample text notes.

EXECUTION:
    pytest backend/tests/test_ner.py
"""

from backend.app.ml.ner_extractor import BioBERTEntityExtractor

def test_biobert_extractor_fallback():
    extractor = BioBERTEntityExtractor()
    sample_note = "Patient has active Type 2 Diabetes and is taking Metformin 500mg daily."
    
    entities = extractor.extract_entities(sample_note)
    
    assert len(entities) > 0
    entity_texts = [e.text.lower() for e in entities]
    assert any("diabetes" in t for t in entity_texts) or any("metformin" in t for t in entity_texts)