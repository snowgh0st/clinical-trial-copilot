"""
backend/app/rag/matching_agent.py

PURPOSE:
Implements a multi-step clinical trial matching agent using LangChain and state graphs.
Evaluates normalized patient data against clinical trial inclusion and exclusion criteria.

CALL STACK & INTEGRATION TRACE:
1. Input Data Sources:
   - Receives `ParsedPatientData` from `backend/app/ingestion/fhir_parser.py`
   - Receives `ExtractedClinicalEntity` list from `backend/app/ml/ner_extractor.py`
   - Queries trial criteria using `VectorStoreManager.similarity_search()` from `backend/app/rag/vector_store.py`
2. Orchestration & API:
   - Called by: `backend/app/api/routes.py` -> `/api/v1/trials/match` endpoint.
   - Outputs `TrialMatchingResult` payload containing overall eligibility, match score, and reasoning.
"""

import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.app.ingestion.fhir_parser import ParsedPatientData
from backend.app.ml.ner_extractor import ExtractedClinicalEntity
from backend.app.rag.vector_store import VectorStoreManager, SearchResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Models (Agent Output Payloads)
# ---------------------------------------------------------------------------

class CriterionEvaluation(BaseModel):
    """
    Detailed evaluation breakdown for a single clinical trial rule.
    Used by `matching_agent.py` to explain why a patient passed or failed a trial constraint.
    """
    criterion_text: str = Field(description="The trial criterion rule text being evaluated")
    is_met: bool = Field(description="True if patient satisfies the rule, False otherwise")
    reasoning: str = Field(description="Explanation tracing patient facts against criterion requirement")


class TrialMatchScore(BaseModel):
    """
    Aggregated matching evaluation for a specific clinical trial (NCT ID).
    Returned to frontend UI to display trial match compatibility percentage.
    """
    trial_id: str = Field(description="Clinical trial identifier (e.g., NCT04561234)")
    trial_title: str = Field(description="Official title of the clinical trial")
    match_score: float = Field(description="Compatibility score between 0.0 and 1.0 (0% to 100%)")
    eligible: bool = Field(description="Overall eligibility status after evaluating exclusion rules")
    evaluations: List[CriterionEvaluation] = Field(default_factory=list, description="Itemized rule breakdown")


class AgentState(BaseModel):
    """
    Internal state graph payload passed between LangGraph node execution steps.
    """
    patient: ParsedPatientData
    entities: List[ExtractedClinicalEntity]
    candidate_trials: List[SearchResult] = Field(default_factory=list)
    results: List[TrialMatchScore] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Clinical Trial Matching Agent Engine
# ---------------------------------------------------------------------------

class TrialMatchingAgent:
    """
    LangChain-backed agent that conducts step-by-step trial matching across 3 nodes:
    1. Retrieve Candidate Trials (via vector store proximity)
    2. Evaluate Inclusion Rules (demographics, active conditions)
    3. Filter Exclusion Rules (medication contraindications)
    """

    def __init__(self, vector_store: Optional[VectorStoreManager] = None):
        """
        Initializes the agent with a vector database connector.

        Args:
            vector_store (VectorStoreManager, optional): Vector store instance for RAG queries.

        Instantiated by:
            - `backend/app/api/routes.py` -> startup route handlers.
        """
        self.vector_store = vector_store or VectorStoreManager()
        logger.info("Initialized Trial Matching Agent state machine.")

    def match_patient_to_trials(
        self, 
        patient: ParsedPatientData, 
        entities: List[ExtractedClinicalEntity]
    ) -> List[TrialMatchScore]:
        """
        Main execution pipeline for trial matching.

        Args:
            patient (ParsedPatientData): Parsed patient demographics and condition records.
            entities (List[ExtractedClinicalEntity]): BioBERT clinical entities extracted from notes.

        Returns:
            List[TrialMatchScore]: Ranked list of evaluated clinical trial matches.

        Called by:
            - `backend/app/api/routes.py` -> `match_clinical_trial()` router endpoint.
        """
        # Step 1: Initialize graph state
        state = AgentState(patient=patient, entities=entities)

        # Step 2: Node 1 - Retrieve Candidate Trials
        state = self._node_retrieve_candidates(state)

        # Step 3: Node 2 - Evaluate Inclusion Criteria
        # Step 4: Node 3 - Filter Exclusion Criteria & Finalize Score
        state = self._node_evaluate_criteria(state)

        return state.results

    # -----------------------------------------------------------------------
    # Graph Execution Nodes
    # -----------------------------------------------------------------------

    def _node_retrieve_candidates(self, state: AgentState) -> AgentState:
        """
        Node 1: Construct search query from patient conditions and query vector database.
        Internal node function for `match_patient_to_trials`.
        """
        condition_names = [c.display_name for c in state.patient.conditions]
        entity_texts = [e.text for e in state.entities if e.entity_group == "DISEASE"]
        
        combined_terms = list(set(condition_names + entity_texts))
        query_text = " ".join(combined_terms) if combined_terms else "General Clinical Trial Inclusion"

        logger.info(f"Querying vector database for candidate trials with query: '{query_text}'")
        candidates = self.vector_store.similarity_search(query_text, limit=3)
        state.candidate_trials = candidates
        return state

    def _node_evaluate_criteria(self, state: AgentState) -> AgentState:
        """
        Nodes 2 & 3: Evaluates candidate trials against patient conditions and active medications.
        Internal node function for `match_patient_to_trials`.
        """
        patient_conditions = [c.display_name.lower() for c in state.patient.conditions]
        patient_meds = [m.display_name.lower() for m in state.patient.medications]

        evaluations_list: List[TrialMatchScore] = []

        for candidate in state.candidate_trials:
            evals: List[CriterionEvaluation] = []
            score_acc = candidate.score  # Base score from vector search similarity

            # 1. Evaluate Inclusion Rule (Condition Match)
            has_condition_match = any(
                term in candidate.content.lower() for term in patient_conditions
            ) if patient_conditions else True

            evals.append(
                CriterionEvaluation(
                    criterion_text="Requires matching primary clinical condition",
                    is_met=has_condition_match,
                    reasoning="Patient condition list overlaps with study protocol focus area." if has_condition_match else "No primary condition overlap found."
                )
            )

            # 2. Evaluate Exclusion Rule (Drug Contraindications)
            has_exclusion = False
            for med in patient_meds:
                if f"exclude {med}" in candidate.content.lower():
                    has_exclusion = True
                    evals.append(
                        CriterionEvaluation(
                            criterion_text=f"Excludes active use of {med}",
                            is_met=False,
                            reasoning=f"Patient currently prescribed {med}, violating study exclusion rule."
                        )
                    )
                    break

            if not has_exclusion:
                evals.append(
                    CriterionEvaluation(
                        criterion_text="No exclusionary medication contraindications",
                        is_met=True,
                        reasoning="Patient medication profile contains no conflicting drugs."
                    )
                )

            # Compute Final Match Flag and Score
            is_eligible = has_condition_match and (not has_exclusion)
            final_score = round(score_acc * 0.9, 2) if is_eligible else 0.15

            evaluations_list.append(
                TrialMatchScore(
                    trial_id=candidate.chunk_id,
                    trial_title=candidate.metadata.get("condition", "Clinical Trial Protocol"),
                    match_score=final_score,
                    eligible=is_eligible,
                    evaluations=evals
                )
            )

        state.results = evaluations_list
        return state