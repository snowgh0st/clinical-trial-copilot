/**
 * frontend/src/services/api.ts
 * 
 * PURPOSE:
 * Typed API client for interacting with the FastAPI backend service.
 */

import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export interface PatientDemographics {
  patient_id: string;
  full_name?: string;
  gender?: string;
  birth_date?: string;
}

export interface ClinicalCondition {
  condition_id: string;
  code: string;
  display_name: string;
  onset_date?: string;
}

export interface MedicationStatement {
  medication_id: string;
  code: string;
  display_name: string;
  status?: string;
}

export interface ParsedPatientData {
  demographics: PatientDemographics;
  conditions: ClinicalCondition[];
  medications: MedicationStatement[];
}

export interface ExtractedClinicalEntity {
  text: string;
  entity_group: string;
  confidence_score: number;
  start_char: number;
  end_char: number;
}

export interface EHRProcessingResponse {
  parsed_patient: ParsedPatientData;
  extracted_entities: ExtractedClinicalEntity[];
  indexed_chunk_id?: string;
}

export interface CriterionEvaluation {
  criterion_text: string;
  is_met: boolean;
  reasoning: string;
}

export interface TrialMatchScore {
  trial_id: string;
  trial_title: string;
  match_score: number;
  eligible: boolean;
  evaluations: CriterionEvaluation[];
}

export interface TrialMatchResponse {
  patient_id: string;
  matches: TrialMatchScore[];
}

export const api = {
  checkHealth: async (): Promise<{ status: string; service: string }> => {
    const res = await axios.get(`${API_BASE_URL}/health`);
    return res.data;
  },

  processEHR: async (payload: { fhir_bundle?: object; clinical_note?: string }): Promise<EHRProcessingResponse> => {
    const res = await axios.post(`${API_BASE_URL}/ehr/upload`, payload);
    return res.data;
  },

  matchTrials: async (payload: {
    parsed_patient: ParsedPatientData;
    extracted_entities: ExtractedClinicalEntity[];
  }): Promise<TrialMatchResponse> => {
    const res = await axios.post(`${API_BASE_URL}/trials/match`, payload);
    return res.data;
  },
};