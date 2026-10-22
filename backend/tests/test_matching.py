"""
backend/tests/test_matching.py

PURPOSE:
Unit tests for `TrialMatchingAgent` verifying eligibility rules and criterion evaluation.

EXECUTION:
    PYTHONPATH=. python -m pytest backend/tests/test_matching.py
"""

from backend.app.ingestion.fhir_parser import ParsedPatientData, PatientDemographics, ClinicalCondition, MedicationStatement
from backend.app.ml.ner_extractor import ExtractedClinicalEntity
from backend.app.rag.vector_store import VectorStoreManager
from backend.app.rag.matching_agent import TrialMatchingAgent

def test_trial_matching_agent():
    patient = ParsedPatientData(
        demographics=PatientDemographics(patient_id="pt-101", full_name="Jane Doe"),
        conditions=[ClinicalCondition(condition_id="c1", code="44054006", display_name="Type 2 Diabetes")],
        medications=[MedicationStatement(medication_id="m1", code="860975", display_name="Metformin")]
    )
    
    entities = [
        ExtractedClinicalEntity(
            text="Type 2 Diabetes", entity_group="DISEASE", confidence_score=0.9, start_char=0, end_char=15
        )
    ]

    vector_store = VectorStoreManager(db_connection_url=None)
    agent = TrialMatchingAgent(vector_store=vector_store)

    results = agent.match_patient_to_trials(patient, entities)

    assert len(results) > 0
    assert results[0].trial_id == "trial-NCT001"
    assert results[0].eligible is True
    assert len(results[0].evaluations) > 0