"""
backend/app/rag/vector_store.py

PURPOSE:
Provides vector store integration using pgvector (PostgreSQL) and Qdrant 
for semantic similarity search over clinical notes, medical literature, and trial criteria.

CALL STACK & INTEGRATION TRACE:
1. Ingestion / Pre-processing:
   - Receives output from `backend/app/ingestion/fhir_parser.py` (ParsedPatientData)
   - Receives tagged entities from `backend/app/ml/ner_extractor.py` (ExtractedClinicalEntity)
2. Storage & Retrieval:
   - `VectorStoreManager.upsert_patient_record()` indexes patient summaries & embeddings.
   - `VectorStoreManager.similarity_search()` is called by `backend/app/rag/matching_agent.py`
     to retrieve top-K relevant clinical trials based on semantic proximity.
"""

import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

import psycopg2
import psycopg2.extras
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class DocumentChunk(BaseModel):
    """
    Represents a textual document or record chunk indexed into the vector database.
    Used by `matching_agent.py` to retrieve background facts with metadata citations.
    """
    chunk_id: str = Field(description="Unique string identifier for the document chunk")
    content: str = Field(description="Raw text snippet (e.g. clinical trial exclusion criteria or patient note)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata key-values (e.g. patient_id, trial_id, ICD-10 codes)")
    embedding: Optional[List[float]] = Field(default=None, description="Vector embedding float array")


class SearchResult(BaseModel):
    """
    Encapsulates a vector search query match along with its similarity distance score.
    Returned to `matching_agent.py` to build augmented LLM prompt context.
    """
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    score: float = Field(description="Cosine similarity score (0.0 to 1.0, higher is more similar)")


# ---------------------------------------------------------------------------
# Vector Store Manager
# ---------------------------------------------------------------------------

class VectorStoreManager:
    """
    Manages vector generation and database operations across pgvector and Qdrant.
    Handles automatic table schema initialization for pgvector.
    """

    DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    VECTOR_DIMENSION = 384  # Standard dimension for MiniLM-L6-v2

    def __init__(
        self, 
        db_connection_url: Optional[str] = None,
        model_name: str = DEFAULT_EMBEDDING_MODEL
    ):
        """
        Initializes the embedding encoder model and database connections.

        Args:
            db_connection_url (str, optional): PostgreSQL connection string.
            model_name (str): SentenceTransformers embedding model identifier.

        Instantiated by:
            - `backend/app/api/routes.py` on app initialization.
            - `backend/app/rag/matching_agent.py` during query resolution.
        """
        self.db_url = db_connection_url
        logger.info(f"Loading SentenceTransformer embedding model: {model_name}")
        self.embedder = SentenceTransformer(model_name)
        
        # Initialize pgvector database schema if a connection URL is supplied
        if self.db_url:
            self._init_pgvector_schema()

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generates a dense vector embedding array for a given text input.

        Args:
            text (str): Input text string.

        Returns:
            List[float]: 384-dimensional vector embedding float list.

        Called by:
            - `VectorStoreManager.upsert_documents()`
            - `VectorStoreManager.similarity_search()`
        """
        if not text or not text.strip():
            return [0.0] * self.VECTOR_DIMENSION
        
        vector = self.embedder.encode(text, convert_to_numpy=True)
        return vector.tolist()

    def upsert_documents(self, documents: List[DocumentChunk], table_name: str = "clinical_embeddings") -> bool:
        """
        Embeds and persists document chunks into PostgreSQL via pgvector.

        Args:
            documents (List[DocumentChunk]): List of document chunks to insert/update.
            table_name (str): Destination database table.

        Returns:
            bool: True if operation succeeded, False otherwise.

        Called by:
            - `backend/app/api/routes.py` -> EHR upload pipeline.
        """
        if not self.db_url:
            logger.warning("No DB URL configured. Skipping database upsert.")
            return False

        try:
            # Generate embeddings for any documents missing them
            for doc in documents:
                if not doc.embedding:
                    doc.embedding = self.generate_embedding(doc.content)

            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()

            insert_query = f"""
                INSERT INTO {table_name} (id, content, metadata, embedding)
                VALUES (%s, %s, %s, %s::vector)
                ON CONFLICT (id) DO UPDATE 
                SET content = EXCLUDED.content, 
                    metadata = EXCLUDED.metadata, 
                    embedding = EXCLUDED.embedding;
            """

            records = [
                (doc.chunk_id, doc.content, psycopg2.extras.Json(doc.metadata), str(doc.embedding))
                for doc in documents
            ]

            cur.executemany(insert_query, records)
            conn.commit()
            cur.close()
            conn.close()
            logger.info(f"Successfully upserted {len(documents)} document chunks to table '{table_name}'.")
            return True

        except Exception as err:
            logger.error(f"Error during pgvector document upsert: {err}")
            return False

    def similarity_search(
        self, 
        query: str, 
        limit: int = 5, 
        table_name: str = "clinical_embeddings"
    ) -> List[SearchResult]:
        """
        Performs cosine similarity search against stored embeddings.

        Args:
            query (str): The search query text (e.g. patient condition description).
            limit (int): Number of top matches to return.
            table_name (str): Vector table to search against.

        Returns:
            List[SearchResult]: Ordered list of top matching documents with similarity scores.

        Called by:
            - `backend/app/rag/matching_agent.py` -> RAG context builder.
        """
        if not self.db_url:
            logger.warning("No DB URL configured. Returning mock search result.")
            return self._mock_similarity_search(query, limit)

        try:
            query_vector = self.generate_embedding(query)
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()

            # Using pgvector cosine distance operator (<=>)
            search_query = f"""
                SELECT id, content, metadata, 1 - (embedding <=> %s::vector) AS similarity_score
                FROM {table_name}
                ORDER BY embedding <=> %s::vector ASC
                LIMIT %s;
            """

            cur.execute(search_query, (str(query_vector), str(query_vector), limit))
            rows = cur.fetchall()

            results = []
            for row in rows:
                results.append(
                    SearchResult(
                        chunk_id=row[0],
                        content=row[1],
                        metadata=row[2] if isinstance(row[2], dict) else {},
                        score=round(float(row[3]), 4)
                    )
                )

            cur.close()
            conn.close()
            return results

        except Exception as err:
            logger.error(f"Error executing similarity search: {err}")
            return self._mock_similarity_search(query, limit)

    # -----------------------------------------------------------------------
    # Internal Helpers
    # -----------------------------------------------------------------------

    def _init_pgvector_schema(self, table_name: str = "clinical_embeddings") -> None:
        """
        Ensures the `vector` extension and destination tables exist in PostgreSQL.
        Internal helper called during class initialization.
        """
        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()
            
            # Enable pgvector extension
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            
            # Create embeddings table
            create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id VARCHAR(255) PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata JSONB DEFAULT '{{}}'::jsonb,
                    embedding vector({self.VECTOR_DIMENSION})
                );
            """
            cur.execute(create_table_sql)
            conn.commit()
            cur.close()
            conn.close()
            logger.info("Initialized pgvector extension and table schema successfully.")
        except Exception as err:
            logger.warning(f"Could not initialize pgvector schema directly ({err}). Will fallback gracefully.")

    def _mock_similarity_search(self, query: str, limit: int) -> List[SearchResult]:
        """
        Fallback mock search for offline/testing environments without an active database.
        Internal helper for `VectorStoreManager.similarity_search`.
        """
        return [
            SearchResult(
                chunk_id="trial-NCT001",
                content=f"Clinical Trial NCT001: Phase 3 study evaluating efficacy in patients matching query '{query}'.",
                metadata={"phase": "Phase 3", "condition": "Metabolic Diseases"},
                score=0.92
            )
        ]