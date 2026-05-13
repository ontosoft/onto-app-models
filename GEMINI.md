# Project Context: Onto Application Models - OntoUI

This workspace contains a full-stack application for generating web applications from knowledge graphs (RDF/SHACL).

## Core Directories & Focus Areas

### 1. Backend: `llm-model-generator/`
**Stack:** Python 3.10+, FastAPI, SQLModel (SQLAlchemy + Pydantic), PostgreSQL.
- **Key Responsibilities:**
  - Managing application models (stored as RDF/Turtle and JSON-LD).
  - RDF processing using `rdflib`.
  - Authentication & User management.
  - Generative AI integration (Ollama).
- **Important Files:**
  - `app/models.py`: Database schemas (User, AppModel).
  - `app/api/routes/`: API endpoints.
  - `app/core/`: Configuration and security logic.

### 2. Frontend: `frontend/`
**Stack:** React, TypeScript, Vite, TanStack Query, TanStack Router, Shadcn UI, Tailwind CSS.
- **Key Responsibilities:**
  - UI for managing models (CRUD operations).
  - Dynamic form generation based on backend models.
  - Interactive knowledge graph editing.
- **Important Files:**
  - `src/routes/`: File-based routing layout.
  - `src/components/`: Reusable UI components.
  - `src/client/`: Auto-generated API client (OpenAPI).

## Interaction Guidelines
- **Backend Changes:** When modifying data models in `models.py`, always consider the impact on `alembic` migrations and the Pydantic schemas used for API validation.
- **Frontend Integration:** The frontend uses a generated client. API changes in the backend usually require updating the `openapi.json` and regenerating the client SDK.
- **RDF/Graph Handling:** The system dual-writes models: as raw Turtle strings (`rdf_content`) and parsed JSON-LD (`knowledge_graph`). Ensure logic keeps these in sync.
