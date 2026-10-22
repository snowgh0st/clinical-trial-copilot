"""
backend/app/ingestion/fhir_parser.py

PURPOSE:
Parses HL7 FHIR (Fast Healthcare Interoperability Resources) R4 JSON bundles 
and normalizes unstructured patient records into clean, structured Python objects.

CALL STACK & INTEGRATION TRACE:
1. API Entrypoint: `backend/app/api/routes.py` receives an EHR payload via `/api/v1/ehr/upload`.
2. Router calls `FHIRParser.parse_bundle(raw_json)` from this file.
3. Outputs `ParsedPatientData` which is passed into:
   - `backend/app/ml/ner_extractor.py` (for deep entity tagging via PyTorch BioBERT)
   - `backend/app/rag/vector_store.py` (for embedding & storing clinical notes in pgvector)
   - `backend/app/rag/matching_agent.py` (for feeding patient facts into LangGraph matching agents)
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Data Models (Normalized Outputs)
# ---------------------------------------------------------------------------

class PatientDemographics(BaseModel):
    """
    Holds core demographic facts extracted from FHIR 'Patient' resources.
    Used by `matching_agent.py` to check age, gender, and regional eligibility criteria.
    """
    patient_id: str = Field(description="Unique FHIR logical identifier for the patient")
    full_name: Optional[str] = Field(default=None, description="Patient full legal name")
    gender: Optional[str] = Field(default=None, description="Administrative gender (male, female, other, unknown)")
    birth_date: Optional[str] = Field(default=None, description="Date of birth in YYYY-MM-DD format")
    telecom: Optional[str] = Field(default=None, description="Primary contact phone or email")


class ClinicalCondition(BaseModel):
    """
    Represents a diagnosed health condition or symptom from FHIR 'Condition' resources.
    Used by `ner_extractor.py` and `matching_agent.py` for inclusion/exclusion trial matching.
    """
    condition_id: str = Field(description="Unique FHIR Condition resource ID")
    code: str = Field(description="SNOMED-CT or ICD-10 code string")
    display_name: str = Field(description="Human-readable condition name (e.g. Type 2 Diabetes Mellitus)")
    clinical_status: str = Field(default="active", description="Status (e.g. active, recurrence, relapse, inactive, resolved)")
    onset_date: Optional[str] = Field(default=None, description="Date or time string when condition began")


class MedicationStatement(BaseModel):
    """
    Represents an active or historic medication prescribed to the patient from FHIR 'MedicationRequest' or 'MedicationStatement'.
    Used by `matching_agent.py` to evaluate drug-drug interaction risks and medication exclusion rules.
    """
    medication_id: str = Field(description="Unique FHIR Medication resource ID")
    code: str = Field(description="RxNorm or local drug code")
    display_name: str = Field(description="Human-readable drug name and dosage")
    status: str = Field(default="active", description="Status (active, completed, stopped, on-hold)")
    authored_on: Optional[str] = Field(default=None, description="Date when medication was prescribed")


class ParsedPatientData(BaseModel):
    """
    Root aggregated container representing the normalized patient record.
    This object serves as the primary data payload passed across backend AI services.
    """
    demographics: PatientDemographics
    conditions: List[ClinicalCondition] = Field(default_factory=list)
    medications: List[MedicationStatement] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Core FHIR Parsing Engine
# ---------------------------------------------------------------------------

class FHIRParser:
    """
    Engine for parsing raw FHIR R4 JSON payloads (Bundles or standalone resource lists).
    """

    @staticmethod
    def parse_bundle(bundle_json: Dict[str, Any]) -> ParsedPatientData:
        """
        Main entrypoint for parsing FHIR Bundles.
        
        Args:
            bundle_json (Dict[str, Any]): The raw deserialized FHIR JSON dictionary.
            
        Returns:
            ParsedPatientData: Normalized patient demographics, conditions, and medications.
            
        Called by:
            - `backend/app/api/routes.py` -> `upload_ehr_record()` endpoint.
        """
        resource_type = bundle_json.get("resourceType", "")
        
        # Check if the incoming payload is a Bundle container or a single resource
        entries = []
        if resource_type == "Bundle":
            entries = bundle_json.get("entry", [])
        else:
            entries = [{"resource": bundle_json}]

        demographics: Optional[PatientDemographics] = None
        conditions: List[ClinicalCondition] = []
        medications: List[MedicationStatement] = []

        for entry in entries:
            resource = entry.get("resource", {})
            rtype = resource.get("resourceType")

            if rtype == "Patient":
                demographics = FHIRParser._extract_demographics(resource)
            elif rtype == "Condition":
                cond = FHIRParser._extract_condition(resource)
                if cond:
                    conditions.append(cond)
            elif rtype in ("MedicationRequest", "MedicationStatement"):
                med = FHIRParser._extract_medication(resource)
                if med:
                    medications.append(med)

        # Fallback if no Patient resource was explicitly present in the bundle
        if not demographics:
            demographics = PatientDemographics(
                patient_id="unknown_patient",
                full_name="Anonymous Patient",
                gender="unknown",
                birth_date=None
            )

        return ParsedPatientData(
            demographics=demographics,
            conditions=conditions,
            medications=medications
        )

    # -----------------------------------------------------------------------
    # Internal Extractor Utilities
    # -----------------------------------------------------------------------

    @staticmethod
    def _extract_demographics(resource: Dict[str, Any]) -> PatientDemographics:
        """
        Parses FHIR 'Patient' resource to extract demographic fields.
        Internal helper for `FHIRParser.parse_bundle`.
        """
        patient_id = resource.get("id", "unknown")
        
        # Parse HumanName
        names = resource.get("name", [])
        full_name = None
        if names:
            primary_name = names[0]
            given = " ".join(primary_name.get("given", []))
            family = primary_name.get("family", "")
            full_name = f"{given} {family}".strip() or None

        # Parse Telecom
        telecoms = resource.get("telecom", [])
        contact = telecoms[0].get("value") if telecoms else None

        return PatientDemographics(
            patient_id=patient_id,
            full_name=full_name,
            gender=resource.get("gender"),
            birth_date=resource.get("birthDate"),
            telecom=contact
        )

    @staticmethod
    def _extract_condition(resource: Dict[str, Any]) -> Optional[ClinicalCondition]:
        """
        Parses FHIR 'Condition' resource into a ClinicalCondition instance.
        Extracts SNOMED/ICD-10 codes and clinical status details.
        Internal helper for `FHIRParser.parse_bundle`.
        """
        cond_id = resource.get("id", "unknown_condition")
        code_concept = resource.get("code", {})
        coding = code_concept.get("coding", [])

        code_val = "UNSPECIFIED"
        display = code_concept.get("text", "Unknown Condition")

        if coding:
            primary_coding = coding[0]
            code_val = primary_coding.get("code", "UNSPECIFIED")
            display = primary_coding.get("display", display)

        # Extract clinical status (active, resolved, etc.)
        status_obj = resource.get("clinicalStatus", {}).get("coding", [])
        status_str = status_obj[0].get("code", "active") if status_obj else "active"

        return ClinicalCondition(
            condition_id=cond_id,
            code=code_val,
            display_name=display,
            clinical_status=status_str,
            onset_date=resource.get("onsetDateTime")
        )

    @staticmethod
    def _extract_medication(resource: Dict[str, Any]) -> Optional[MedicationStatement]:
        """
        Parses FHIR 'MedicationRequest' or 'MedicationStatement' into a MedicationStatement instance.
        Internal helper for `FHIRParser.parse_bundle`.
        """
        med_id = resource.get("id", "unknown_medication")
        
        # Handle CodeableConcept for medication
        med_concept = resource.get("medicationCodeableConcept", {})
        coding = med_concept.get("coding", [])

        code_val = "UNSPECIFIED"
        display = med_concept.get("text", "Unknown Medication")

        if coding:
            primary_coding = coding[0]
            code_val = primary_coding.get("code", "UNSPECIFIED")
            display = primary_coding.get("display", display)

        status = resource.get("status", "active")
        authored = resource.get("authoredOn") or resource.get("effectiveDateTime")

        return MedicationStatement(
            medication_id=med_id,
            code=code_val,
            display_name=display,
            status=status,
            authored_on=authored
        )