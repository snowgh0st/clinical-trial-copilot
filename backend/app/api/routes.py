"""
backend/app/api/routes.py

PURPOSE:
Exposes HTTP endpoints for EHR/FHIR bundle ingestion, BioBERT clinical entity extraction,
vector embeddings indexing, and multi-step clinical trial matching.

CALL STACK & INTEGRATION TRACE:
1. Called by: `backend/app/main.py` -> mounted via `app.include_router(router, prefix="/api/v1")`.
2. Integrates:
   - `FHIRParser` from `backend/app/ingestion/fhir_parser.py`
   - `BioBERTEntityExtractor` from `backend/app/ml/ner_extractor.py`
   - `VectorStoreManager` from `backend/app/rag/vector_store.py`
   - `TrialMatchingAgent` from `backend/app/rag/matching_agent.py`
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from opentelemetry.trace import Status
from opentelemetry.trace import Status
from pydantic import BaseModel, Field

from backend.app.ingestion.fhir_parser import FHIRParser, ParsedPatientData, PatientDemographics
from backend.app.ml.ner_extractor import BioBERTEntityExtractor, ExtractedClinicalEntity
from backend.app.rag.vector_store import VectorStoreManager, DocumentChunk
from backend.app.rag.matching_agent import TrialMatchingAgent, TrialMatchScore

logger = logging.getLogger(__name__)

router = APIRouter()

# Singletons / Dependency Instances
fhir_parser = FHIRParser()
ner_extractor = BioBERTEntityExtractor()
vector_store = VectorStoreManager()
matching_agent = TrialMatchingAgent(vector_store=vector_store)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class EHRUploadRequest(BaseModel):
    """
    Request payload accepting either a raw FHIR JSON bundle or plain clinical text.
    """
    fhir_bundle: Optional[Dict[str, Any]] = Field(default=None, description="Raw HL7 FHIR JSON bundle")
    clinical_note: Optional[str] = Field(default=None, description="Free-text clinical physician note")


class EHRProcessingResponse(BaseModel):
    """
    Combined analysis payload returned to the frontend.
    """
    parsed_patient: ParsedPatientData
    extracted_entities: List[ExtractedClinicalEntity]
    indexed_chunk_id: Optional[str] = Field(default=None, description="Vector store record ID")


class TrialMatchRequest(BaseModel):
    """
    Request payload to match a patient against active trial database.
    """
    parsed_patient: ParsedPatientData
    extracted_entities: List[ExtractedClinicalEntity] = Field(default_factory=list)


class TrialMatchResponse(BaseModel):
    """
    Response containing compatibility evaluations across target clinical trials.
    """
    patient_id: str
    matches: List[TrialMatchScore]


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, str]:
    """
    Simple system health check endpoint.
    """
    return {
        "status": "healthy",
        "service": "clinical-trial-copilot-backend"
    }


@router.post("/ehr/upload", response_model=EHRProcessingResponse, status_code=status.HTTP_200_OK)
async def process_ehr(payload: EHRUploadRequest) -> EHRProcessingResponse:
    """
    Ingests EHR data (FHIR bundle or note), extracts entities via BioBERT, 
    and indexes the summary into the vector database.
    """
    if not payload.fhir_bundle and not payload.clinical_note:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either a fhir_bundle or clinical_note."
        )

    # 1. Parse FHIR Bundle or create baseline
    if payload.fhir_bundle:
        parsed_patient = fhir_parser.parse_bundle(payload.fhir_bundle)
    else:
        parsed_patient = ParsedPatientData(
            demographics=PatientDemographics(
                patient_id="pt-note-01", 
                full_name="Anonymous Patient"
            )
        )

    # 2. Extract BioBERT entities from note or conditions
    note_text = payload.clinical_note or " ".join([c.display_name for c in parsed_patient.conditions])
    extracted_entities = ner_extractor.extract_entities(note_text)

    # 3. Index into Vector Store
    chunk_id = f"doc-{parsed_patient.demographics.patient_id}"
    chunk = DocumentChunk(
        chunk_id=chunk_id,
        content=f"Patient {parsed_patient.demographics.patient_id}: {note_text}",
        metadata={"patient_id": parsed_patient.demographics.patient_id}
    )
    vector_store.upsert_documents([chunk])

    return EHRProcessingResponse(
        parsed_patient=parsed_patient,
        extracted_entities=extracted_entities,
        indexed_chunk_id=chunk_id
    )


@router.post("/trials/match", response_model=TrialMatchResponse, status_code=status.HTTP_200_OK)
async def match_trials(payload: TrialMatchRequest) -> TrialMatchResponse:
    """
    Runs the LangChain/LangGraph trial matching agent against patient data and entities.
    """
    try:
        matches = matching_agent.match_patient_to_trials(
            patient=payload.parsed_patient,
            entities=payload.extracted_entities
        )

        return TrialMatchResponse(
            patient_id=payload.parsed_patient.demographics.patient_id,
            matches=matches
        )
    except Exception as err:
        logger.error(f"Error during trial matching: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trial matching engine failure: {str(err)}"
        )