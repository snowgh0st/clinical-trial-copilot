"""
backend/app/ml/ner_extractor.py

PURPOSE:
Performs deep clinical Named Entity Recognition (NER) on unstructured EHR text 
and medical notes using PyTorch and BioBERT (dmis-lab/biobert-v1.1).

CALL STACK & INTEGRATION TRACE:
1. Called by: `backend/app/api/routes.py` -> during `/api/v1/ehr/upload` post-processing.
2. Accepts output from: `backend/app/ingestion/fhir_parser.py` (specifically raw text notes or condition descriptions).
3. Outputs structured `ExtractedClinicalEntity` list passed into:
   - `backend/app/rag/matching_agent.py` (to verify inclusion/exclusion trial criteria).
   - `backend/app/rag/vector_store.py` (stored as metadata tags for hybrid vector search).
"""

import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class ExtractedClinicalEntity(BaseModel):
    """
    Represents a single clinical entity identified by the PyTorch BioBERT model.
    Used by `matching_agent.py` to match against clinical trial eligibility criteria.
    """
    text: str = Field(description="The extracted entity text (e.g., 'Metformin', 'Type 2 Diabetes')")
    entity_group: str = Field(description="Entity classification category (e.g., DISEASE, CHEMICAL, PROCEDURE)")
    confidence_score: float = Field(description="Model prediction confidence score between 0.0 and 1.0")
    start_char: int = Field(description="Start character index in original clinical text")
    end_char: int = Field(description="End character index in original clinical text")


# ---------------------------------------------------------------------------
# PyTorch BioBERT Entity Extractor Class
# ---------------------------------------------------------------------------

class BioBERTEntityExtractor:
    """
    Loads and executes a PyTorch BioBERT model for domain-specific medical NER.
    Handles device selection (GPU/CUDA vs CPU) automatically.
    """

    DEFAULT_MODEL_NAME = "dmis-lab/biobert-v1.1"

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME):
        """
        Initializes the model tokenizer and inference pipeline.
        
        Args:
            model_name (str): Hugging Face model identifier for BioBERT.
            
        Instantiated by:
            - `backend/app/api/routes.py` on FastAPI startup event.
        """
        self.model_name = model_name
        
        # Determine execution device: "cuda" if available, otherwise "cpu"
        device_str = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Initializing BioBERT Entity Extractor on {device_str.upper()} using model: {model_name}")

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForTokenClassification.from_pretrained(model_name)
            
            # Setup Hugging Face NER pipeline with PyTorch backend
            self.ner_pipeline = pipeline(
                "token-classification",  # Explicit task string matches pipeline overloads cleanly
                model=self.model,
                tokenizer=self.tokenizer,
                aggregation_strategy="simple",
                device=device_str
            )
        except Exception as e:
            logger.warning(f"Failed to load BioBERT weights ({str(e)}). Falling back to rule-based parser.")
            self.ner_pipeline = None

    def extract_entities(self, text: str) -> List[ExtractedClinicalEntity]:
        """
        Extracts clinical entities from unstructured medical text.

        Args:
            text (str): Free-text clinical narrative or physician notes.

        Returns:
            List[ExtractedClinicalEntity]: List of normalized entity records.

        Called by:
            - `backend/app/api/routes.py` -> `extract_clinical_facts()` endpoint.
            - `backend/app/rag/matching_agent.py` -> criterion validation step.
        """
        if not text or not text.strip():
            return []

        # Fallback to lightweight regex parsing if HuggingFace pipeline fails to load
        if not self.ner_pipeline:
            return self._fallback_keyword_extraction(text)

        try:
            raw_entities = self.ner_pipeline(text)
            results: List[ExtractedClinicalEntity] = []

            for entity in raw_entities:
                results.append(
                    ExtractedClinicalEntity(
                        text=entity.get("word", "").strip(),
                        entity_group=entity.get("entity_group", "CLINICAL_TERM"),
                        confidence_score=round(float(entity.get("score", 0.0)), 4),
                        start_char=int(entity.get("start", 0)),
                        end_char=int(entity.get("end", 0))
                    )
                )

            return results

        except Exception as err:
            logger.error(f"PyTorch BioBERT inference error: {err}")
            return self._fallback_keyword_extraction(text)

    def _fallback_keyword_extraction(self, text: str) -> List[ExtractedClinicalEntity]:
        """
        Heuristic fallback method used when PyTorch model weights are offline.
        Internal helper for `BioBERTEntityExtractor.extract_entities`.
        """
        logger.info("Executing rule-based clinical keyword extractor fallback.")
        entities: List[ExtractedClinicalEntity] = []
        
        common_indicators = [
            ("diabetes", "DISEASE"),
            ("hypertension", "DISEASE"),
            ("carcinoma", "DISEASE"),
            ("metformin", "CHEMICAL"),
            ("lisinopril", "CHEMICAL"),
            ("chemotherapy", "PROCEDURE"),
            ("biopsy", "PROCEDURE")
        ]

        text_lower = text.lower()
        for word, cat in common_indicators:
            start_idx = text_lower.find(word)
            if start_idx != -1:
                entities.append(
                    ExtractedClinicalEntity(
                        text=word.capitalize(),
                        entity_group=cat,
                        confidence_score=0.85,
                        start_char=start_idx,
                        end_char=start_idx + len(word)
                    )
                )

        return entities