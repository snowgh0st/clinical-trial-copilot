# Clinical Trial Copilot 🏥🤖

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![LangChain](https://img.shields.io/badge/LangChain-Agent-1C3C3C?logo=chainlink&logoColor=white)](https://www.langchain.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38Bdf8?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📌 Overview

**Clinical Trial Copilot** is an advanced full-stack AI engineering application designed to streamline clinical trial recruitment and patient eligibility screening. The system ingests electronic health records (EHRs)—supporting both HL7 FHIR R4 JSON bundles and unstructured clinical notes—extracts biomedical entities using PyTorch BioBERT, indexes semantic embeddings via PostgreSQL (`pgvector`), and executes multi-step RAG-based eligibility evaluations through LangChain and LangGraph.

---

## 🚀 Key Features

* **HL7 FHIR R4 & Clinical Note Ingestion**: Parses normalized patient demographics, medical conditions, and medication statements from structured FHIR JSON or unstructured physician notes.
* **PyTorch BioBERT NER Pipeline**: Extracts biomedical entities (diseases, medications, procedures) with confidence scores and category grouping.
* **Semantic Vector Search (`pgvector`)**: Chunks and indexes patient records into a high-performance vector store for similarity matching.
* **LangChain / LangGraph Matching Agent**: Evaluates patient profiles against candidate trial criteria, returning inclusion/exclusion breakdowns and overall compatibility percentages.
* **Modern React Dashboard**: Built with Vite, React, TypeScript, and Tailwind CSS featuring interactive entity badge displays and expandable trial evaluation cards.

---

## 🏗️ Architecture Diagram

```text
       [ React + TypeScript + Tailwind Frontend ]
                        │
                        ▼  (REST API / JSON)
               [ FastAPI Backend ]
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
  [ FHIR Parser ]  [ BioBERT NER ]  [ pgvector Store ]
         │              │              │
         └──────────────┼──────────────┘
                        ▼
         [ LangChain / LangGraph Agent ]
                        │
                        ▼
         [ Clinical Trial Compatibility ]
```

---

## 🧰 Tech Stack

* **Backend**: Python, FastAPI, Pydantic v2, Uvicorn
* **Machine Learning / NLP**: PyTorch, Hugging Face Transformers (`dmis-lab/biobert-v1.1`), SentenceTransformers
* **RAG & Agents**: LangChain, LangGraph, PostgreSQL with `pgvector`
* **Frontend**: React, TypeScript, Vite, Tailwind CSS, Lucide React, Axios

---

## ⚙️ Local Development & Setup

### Prerequisites

* Python 3.11+
* Node.js 18+ & npm
* PostgreSQL with `pgvector` extension enabled

### 1. Backend Setup

```bash
# Clone the repository
git clone [https://github.com/your-username/clinical-trial-copilot.git](https://github.com/your-username/clinical-trial-copilot.git)
cd clinical-trial-copilot

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install package in editable mode with dependencies
pip install -e .

# Run FastAPI development server
uvicorn backend.app.main:app --reload --port 8000

```

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev

```

### 3. Running Backend Tests

```bash
python -m pytest backend/tests/

```

---

## 🔌 API Reference

### Base URL: `http://localhost:8000/api/v1`

| Endpoint | Method | Description | Payload Example |
| --- | --- | --- | --- |
| `/health` | `GET` | Health check and service status | None |
| `/ehr/upload` | `POST` | Ingests EHR data, runs BioBERT NER, and indexes to vector store | `{"clinical_note": "Patient with Type 2 Diabetes..."}` or `{"fhir_bundle": {...}}` |
| `/trials/match` | `POST` | Executes LangChain matching agent against candidate trials | `{"parsed_patient": {...}, "extracted_entities": [...]}` |

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.

