# OmniSight

OmniSight is a multimodal agentic RAG project for e-commerce restocking decisions.

## Phase 1
This phase sets up:

- project folder structure
- Python environment
- config management
- local Ollama / OpenAI provider switch
- Qdrant Docker setup
- basic smoke test

## Run setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
docker compose up -d