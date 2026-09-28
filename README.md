# Chleo Lite - Autonomous Real Estate Lead Qualification Agent

Chleo Lite is an Ironhack Autonomous Agent Challenge Lab for a fictional Mallorca real-estate lead qualification workflow.

## Current Status

- Project planning: Complete
- Architecture design: Complete
- Offline minimal prototype: Complete
- Automated tests: Complete
- LangGraph integration: Planned, not implemented
- Vector RAG with Chroma: Planned, not implemented
- n8n integration: Planned, not implemented
- Deployment: Out of scope

## Repository Structure

```text
.
|-- README.md
|-- demo.py
|-- pyproject.toml
|-- project_plan.md
|-- lab_summary.md
|-- requirements.txt
|-- .env.example
|-- .gitignore
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
|   |-- test_models.py
|   |-- test_rag.py
|   `-- test_scoring.py
`-- artifacts/
    `-- README.md
```

## What This Prototype Does

The implemented offline prototype uses local deterministic extraction, exact business filters, offline property retrieval, explainable scoring, a local state-machine workflow, and mandatory human review. It does not use LangGraph, Chroma, n8n, OpenAI API calls, or deployment services yet.

## Run the Offline Demo

```powershell
C:\Python314\python.exe demo.py --lead-id LEAD-001
C:\Python314\python.exe demo.py --lead-id LEAD-001 --decision approve
C:\Python314\python.exe demo.py --inquiry "I am looking for an apartment in Palma with a budget of â‚¬350,000."
```

```bash
python demo.py --lead-id LEAD-001
```

A complete sample reaches human review. An incomplete inquiry returns one follow-up question. `--decision approve` applies an explicit human decision. No customer communication occurs.

## Run the Tests

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

## Installation

Install the runtime dependencies with:

```bash
pip install -r requirements.txt
```

## Documentation

- [project_plan.md](project_plan.md)
- [docs/architecture.md](docs/architecture.md)
- [lab_summary.md](lab_summary.md)
- [n8n/README.md](n8n/README.md)

## Data and Privacy

All property and lead data are fictional. No real personal data, API keys, or customer information should be added to this repository.
