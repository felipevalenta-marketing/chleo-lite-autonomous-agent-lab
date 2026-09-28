# Chleo Lite – Autonomous Real Estate Lead Qualification Agent

Chleo Lite is an Ironhack Autonomous Agent Challenge Lab. It plans and validates a small AI-assisted workflow for qualifying fictional buyer inquiries for a fictional micro real estate agency in Mallorca.

## Project Purpose

Incoming real estate inquiries are reviewed manually, so information is often incomplete and staff must ask follow-up questions before they can judge the lead. Property searches and lead prioritisation also depend on staff time and judgement. Chleo Lite proposes a controlled workflow that supports the team without replacing human decisions.

## Planned MVP

- Accept one fictional English-language inquiry
- Extract the six required lead fields
- Detect missing information
- Generate one follow-up question at a time
- Search a fictional property catalogue
- Apply deterministic budget and availability filters
- Calculate an explainable lead score
- Classify the lead as hot, warm or cold
- Prepare a recommendation
- Pause for mandatory human review
- Display the result locally

No message is automatically sent to a customer.

## Technology Stack

| Technology | Planned role |
|---|---|
| Python | Core implementation language |
| Streamlit | Local prototype interface |
| OpenAI chat model | Planned text extraction and follow-up generation |
| OpenAI embeddings | Planned semantic representation for property documents |
| LangChain | Prompt and retrieval building blocks |
| LangGraph | Workflow orchestration and conditional routing |
| Chroma | Local vector store for fictional property data |
| Pydantic | Data validation for leads and properties |
| pytest | Planned automated tests |
| n8n | Future orchestration and external workflow integration |

## Repository Structure

```text
.
|-- README.md
|-- project_plan.md
|-- lab_summary.md
|-- requirements.txt
|-- .env.example
|-- .gitignore
|-- app/
|   `-- streamlit_app.py
|-- data/
|   |-- sample_leads.json
|   `-- sample_properties.json
|-- docs/
|   `-- architecture.md
|-- n8n/
|   `-- README.md
|-- src/
|   `-- chleo/
|       |-- __init__.py
|       |-- config.py
|       |-- models.py
|       |-- graph.py
|       |-- nodes.py
|       |-- rag.py
|       `-- scoring.py
|-- tests/
|   |-- __init__.py
|   |-- test_graph.py
|   |-- test_rag.py
|   `-- test_scoring.py
`-- artifacts/
    `-- README.md
```

| Path | Purpose |
|---|---|
| `project_plan.md` | Main planning document |
| `lab_summary.md` | Final reflection placeholder |
| `docs/architecture.md` | Technical architecture and workflow design |
| `n8n/README.md` | Future n8n workflow notes |
| `app/streamlit_app.py` | Placeholder for the future local prototype UI |
| `src/chleo/` | Planned Python package for the agent modules |
| `data/` | Fictional sample leads and properties |
| `tests/` | Planned test files |
| `artifacts/` | Submission evidence folder |

## Required Lab Deliverables

The required planning deliverables are `project_plan.md` and `lab_summary.md`. `docs/architecture.md` is an additional technical-design artifact. The prototype is optional under the original lab brief.

## Current Status

- Project planning: Complete
- Architecture design: Complete
- Repository scaffold: Complete
- Minimal prototype: Not implemented yet
- n8n workflow: Planned only
- Deployment: Out of scope

## Planned Prototype Flow

Inquiry -> extraction -> completeness check -> follow-up if needed -> property retrieval -> deterministic filtering -> lead scoring -> recommendation -> human review -> local result

See [docs/architecture.md](docs/architecture.md) for the detailed diagrams.

## Installation and Execution

Installation and execution instructions will be added after the optional prototype is implemented.

## Data and Privacy

- All leads and properties are fictional.
- No real personal data belongs in this repository.
- API keys must be stored in `.env`.
- `.env` must not be committed.
- Human approval is required before future customer contact.
- The prototype must not provide legal, financial, or mortgage advice.

## Documentation

- [project_plan.md](project_plan.md)
- [docs/architecture.md](docs/architecture.md)
- [lab_summary.md](lab_summary.md)
- [n8n/README.md](n8n/README.md)

## Scope Boundaries

The MVP excludes real customers, live property portals, production CRM connections, automatic messages, multilingual conversations, financial or legal advice, and production deployment.

## Author

Carlos Felipe Valencia Taborda  
Ironhack AI Consulting & Integration Bootcamp
