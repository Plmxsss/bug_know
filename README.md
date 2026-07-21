# AgriGuard AI

AgriGuard AI is a learning-driven agricultural pest detection and knowledge
question-answering project. The finished system will connect a trained IP102
YOLO model, FastAPI, MySQL, Qdrant RAG, local or API-hosted language models,
and a Vue 3 frontend.

The repository is built in small, verifiable stages. The current stage contains
only the backend foundation and a health-check endpoint. Database access, YOLO
inference, RAG, LLM integration, and the frontend are intentionally deferred.

## Requirements

- Python 3.11 or newer
- PowerShell examples below; equivalent commands work in other shells

## Run the current stage

Create and activate a Python 3.11 Conda environment from the repository root:

```powershell
conda create -n agriguard-app python=3.11 -y
conda activate agriguard-app
python -m pip install --upgrade pip
python -m pip install -e ".\backend[dev]"
```

Keep an older training environment separate instead of upgrading its Python in
place. Binary packages such as PyTorch and OpenCV are tied to a Python version;
the trained `.pt` weight can later be validated from the application environment.

Start the API from the `backend` directory:

```powershell
Set-Location backend
uvicorn app.main:app --reload
```

Open:

- API health check: <http://127.0.0.1:8000/api/v1/health>
- Swagger UI: <http://127.0.0.1:8000/docs>
- OpenAPI schema: <http://127.0.0.1:8000/openapi.json>

## Test and check

Run these commands from `backend` with the virtual environment active:

```powershell
pytest
ruff check .
mypy app
```

Expected health response:

```json
{
  "status": "ok",
  "service": "agriguard-api",
  "version": "0.1.0"
}
```

## Existing model assets

The previously trained IP102 dataset, scripts, weights, and experiment outputs
remain under the local `data/` directory. That directory is ignored by Git to
avoid committing large datasets and binary artifacts. A later stage will create
a reproducible model manifest without modifying the original training outputs.
