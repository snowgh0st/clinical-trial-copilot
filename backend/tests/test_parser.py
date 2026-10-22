"""
backend/tests/test_parser.py

PURPOSE:
Unit tests for `FHIRParser` to ensure correct extraction of Patient, Condition, 
and MedicationRequest resources from sample FHIR JSON payloads.

EXECUTION:
Run from project root:
    pytest backend/tests/test_parser.py
"""

from backend.app.ingestion.fhir_parser import FHIRParser

SAMPLE_FHIR_BUNDLE = {
    "resourceType": "Bundle",
    "entry": [
        {
            "resource": {
                "resourceType": "Patient",
                "id": "pt-101",
                "name": [{"given": ["Jane"], "family": "Doe"}],
                "gender": "female",
                "birthDate": "1985-04-12"
            }
        },
        {
            "resource": {
                "resourceType": "Condition",
                "id": "cond-201",
                "code": {
                    "coding": [{"code": "44054006", "display": "Type 2 Diabetes Mellitus"}]
                },
                "clinicalStatus": {"coding": [{"code": "active"}]}
            }
        },
        {
            "resource": {
                "resourceType": "MedicationRequest",
                "id": "med-301",
                "medicationCodeableConcept": {
                    "coding": [{"code": "860975", "display": "Metformin 500 MG Oral Tablet"}]
                },
                "status": "active"
            }
        }
    ]
}

def test_fhir_parser_bundle():
    parsed = FHIRParser.parse_bundle(SAMPLE_FHIR_BUNDLE)

    assert parsed.demographics.patient_id == "pt-101"
    assert parsed.demographics.full_name == "Jane Doe"
    assert parsed.demographics.gender == "female"
    
    assert len(parsed.conditions) == 1
    assert parsed.conditions[0].display_name == "Type 2 Diabetes Mellitus"
    assert parsed.conditions[0].code == "44054006"

    assert len(parsed.medications) == 1
    assert parsed.medications[0].display_name == "Metformin 500 MG Oral Tablet"
    assert parsed.medications[0].status == "active"