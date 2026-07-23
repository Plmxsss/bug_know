# AgriGuard AI

AgriGuard AI is a learning-driven agricultural pest detection and knowledge
question-answering project. The finished system will connect a trained IP102
YOLO model, FastAPI, MySQL, Qdrant RAG, local or API-hosted language models,
and a Vue 3 frontend.

The repository is built in small, verifiable stages. The current stage can
validate and store an uploaded image, run the trained IP102 YOLO model on GPU,
draw an annotated result, and persist the task and bounding boxes in MySQL.
It can also upload, parse, chunk, locally embed, and index provenance-rich
knowledge sources in MySQL and Qdrant. Retrieval, LLM integration, and the
frontend remain in progress.

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

Install the optional YOLO inference dependencies:

```powershell
python -m pip install -e ".\backend[dev,ml]"
```

The default Python package source may install CPU-only PyTorch. On this project's
CUDA 12.8 Windows workstation, install the verified GPU build from the official
PyTorch package source:

```powershell
python -m pip install --force-reinstall `
  torch==2.8.0 torchvision==0.23.0 `
  --index-url https://download.pytorch.org/whl/cu128
```

Verify that the result prints `True`:

```powershell
python -c "import torch; print(torch.cuda.is_available())"
```

Enable lifespan model loading in the private root `.env` only after the ML
dependencies and local weight are available:

```dotenv
AGRIGUARD_YOLO_ENABLED=true
AGRIGUARD_YOLO_DEVICE=0
```

When disabled, API and database development can run without importing PyTorch.

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
- API and MySQL readiness check: <http://127.0.0.1:8000/api/v1/health/ready>
- Detection task history: <http://127.0.0.1:8000/api/v1/detections>
- Detection task example: <http://127.0.0.1:8000/api/v1/detections/1>
- Generated annotation example: <http://127.0.0.1:8000/media/annotated/FILE.jpg>
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

## Run the local MySQL database

Copy the example configuration once, then replace its example passwords:

```powershell
Copy-Item .env.example .env
```

Start MySQL and Qdrant from the repository root:

```powershell
docker compose --env-file .env -f infra/compose.yaml up -d mysql qdrant
docker compose --env-file .env -f infra/compose.yaml ps
```

The Compose port mapping makes the MySQL process inside the container available
to FastAPI at `127.0.0.1:3306` and Qdrant's HTTP API at
`127.0.0.1:6333`. Qdrant data uses a named Docker volume rather than a Windows
bind mount. After starting the containers and FastAPI, verify both connections:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/ready
```

Expected response:

```json
{
  "status": "ready",
  "database": "ok",
  "vector_database": "ok"
}
```

This endpoint executes `SELECT 1` in MySQL and requests Qdrant collection
metadata. It returns HTTP 503 with a service-specific error code when either
dependency cannot be reached, while `/api/v1/health` continues to report
whether FastAPI itself is running.

## Run a real image detection

Make sure MySQL is migrated, the model version is registered as active, and
`AGRIGUARD_YOLO_ENABLED=true` is set in the private `.env`. Then either use the
Swagger `POST /api/v1/detections` form or run this command from `backend`:

```powershell
curl.exe -X POST `
  -F "image=@../data/image/IP000000000.jpg;type=image/jpeg" `
  http://127.0.0.1:8000/api/v1/detections
```

The API accepts matching JPEG, PNG, or WebP content, creates a generated
filename instead of trusting the upload name, limits both compressed bytes and
decoded pixels, serializes GPU access inside one process, and returns a public
annotation URL. A successful request also inserts one `detection_tasks` row and
zero or more linked `detection_objects` rows.

## Apply database migrations

Run Alembic commands from the `backend` directory with MySQL running:

```powershell
Set-Location backend
alembic upgrade head
alembic current
```

`upgrade head` applies every migration through the newest revision. To undo
only the latest revision and then restore it:

```powershell
alembic downgrade -1
alembic upgrade head
```

Alembic reads the same private root `.env` file as the API. Database passwords
are not stored in `alembic.ini` or migration files.

## Register the trained model

After applying migrations, register the local IP102 weights from the `backend`
directory:

```powershell
python scripts/register_model_version.py `
  --name ip102-yolo26n `
  --version 1.0.0 `
  --weights-path ..\data\runs\yolo26n_bug_know-5\weights\best.pt `
  --class-count 102 `
  --active
```

The command calculates the file's SHA-256 fingerprint, inserts the record, and
prints its database-generated ID and creation time. Running the same name and
version again returns the existing row instead of inserting a duplicate.

Create a pending detection task for a local image:

```powershell
python scripts/create_detection_task.py `
  --model-version-id 1 `
  --image-path ..\data\image\IP000000000.jpg
```

The referenced model version must already exist. MySQL rejects a task whose
`model_version_id` does not match a row in `model_versions`.

Development-only status transition examples:

```powershell
# Replace 123 with the ID printed by create_detection_task.py.
python scripts/update_detection_task_status.py --task-id 123 start

python scripts/update_detection_task_status.py `
  --task-id 123 `
  fail `
  --error-message "Inference worker stopped."
```

The service permits `pending -> processing -> completed` and failure from
`pending` or `processing`. Invalid transitions return a business error.

Seed the 102 labels from the exact training dataset configuration:

```powershell
python scripts/seed_pest_mappings.py
```

The first run creates entity skeletons, Chinese aliases, and model-class
mappings. Every entity starts with `knowledge_status=missing`, and every mapping
starts with `mapping_status=needs_review`; this intentionally prevents
unreviewed labels from entering RAG. Re-running the command is idempotent and
does not duplicate rows.

Detection responses expose `normalization_status`. Only a `verified` mapping
may populate `normalized_entity_id`; `unmapped` and `needs_review` results stay
null. Entity identity and knowledge readiness are separate: even a verified
identity with `knowledge_status=missing` must not be used to generate a RAG
answer.

Verify mappings one model version and class at a time after checking the
training catalog and normalized entity:

```powershell
python scripts/review_pest_mapping.py `
  --class-id 0 `
  --expected-label 稻纵卷叶螟 `
  --expected-entity-code ip102-class-000 `
  --reviewed-by project-maintainer `
  --note "Matched the training catalog and curated entity record."
```

The command fails without changing the row if either expected value is wrong.
A successful review records UTC time, reviewer label, and note. It verifies
only the model-to-entity identity; it does not promote indexed knowledge from
`draft` to `reviewed`.

Upload a provenance-rich PDF, UTF-8 text file, or Markdown source through
Swagger at `POST /api/v1/documents`. Required form fields are `file`, `title`,
`source_organization`, and one or more `entity_ids`; URL, publication date, and
region are optional but strongly recommended. Files are stored by SHA-256, and
byte-identical uploads return HTTP 409. The committed
`knowledge_sources/` directory contains curated, source-linked inputs used by
the reproducible demo; an uploaded document is not searchable until the later
indexing step succeeds.

Install the optional local RAG dependencies and enable the embedding model:

```powershell
python -m pip install -e ".\backend[dev,rag]"
```

```dotenv
AGRIGUARD_EMBEDDING_ENABLED=true
AGRIGUARD_EMBEDDING_DEVICE=cpu
```

Restart FastAPI after changing `.env`, then call
`POST /api/v1/documents/{document_id}/index` in Swagger. Indexing performs these
steps in order:

1. mark the document as `processing`;
2. parse it into titled sections and deterministic chunks;
3. generate normalized 512-dimensional vectors locally with
   `BAAI/bge-small-zh-v1.5`;
4. upsert entity-filterable vector points into Qdrant;
5. save the exact chunk text and citation locator in MySQL;
6. mark the document `indexed` and its linked entity knowledge `draft`.

The embedding model runs on CPU by default so it does not compete with YOLO
for GPU memory. `draft` means that indexing succeeded but a person has not yet
approved the knowledge for diagnosis. Calling the endpoint while embedding is
disabled returns HTTP 503; indexing the same already-indexed document returns
HTTP 409 rather than silently replacing reviewed data.

After an intentional parsing or chunking change, explicitly rebuild an indexed
document with
`POST /api/v1/documents/{document_id}/index?reindex=true`. The service upserts
deterministic replacement points and deletes obsolete Qdrant point IDs.
Headings used only for structured provenance, such as `来源信息`, are stored as
document metadata but excluded from embeddings so they do not consume Top-K
semantic result slots.

Test retrieval independently from the later language-model step through
Swagger at `POST /api/v1/knowledge/search`:

```json
{
  "entity_id": 1,
  "query": "稻纵卷叶螟幼虫如何危害水稻叶片？",
  "top_k": 3
}
```

Qdrant first applies an exact `pest_entity_id` payload filter and then ranks
only that entity's chunks by cosine similarity. The service uses the returned
point IDs to read the original text and citation fields from MySQL; a Qdrant
point with no matching indexed MySQL chunk is discarded. A response includes
the entity's `missing`, `draft`, or `reviewed` status so later diagnosis code
can require human-reviewed knowledge even though this inspection endpoint
allows draft retrieval.

Promote one entity from `draft` to `reviewed` only after reading its indexed
sources and checking the regional and safety boundaries:

```powershell
python scripts/review_pest_knowledge.py `
  --entity-code ip102-class-000 `
  --expected-common-name 稻纵卷叶螟 `
  --reviewed-by project-maintainer `
  --note "Reviewed source content, citations, regional limits, and safety."
```

The automated gate requires at least two indexed documents with retrievable
chunks, at least two distinct source organizations, and a source URL for every
document. These objective checks do not replace content review; the reviewer
and note are recorded with UTC time for auditability.

## Configure a language-model provider

The backend uses one `LLMProvider` interface for both local and cloud-hosted
models. Its first implementation calls an OpenAI-compatible
`/v1/chat/completions` endpoint, requests structured JSON, and validates the
returned content with Pydantic before business code can use it. Temporary
network errors and selected HTTP statuses are retried against the same
provider; local failure does not automatically send data to a cloud service.

For the default Windows development setup, install Ollama and pull the official
Qwen3 4B non-thinking instruct quantization:

```powershell
ollama pull qwen3:4b-instruct-2507-q4_K_M
ollama list
```

Then set the private `.env`:

```dotenv
AGRIGUARD_LLM_ENABLED=true
AGRIGUARD_LLM_PROVIDER=ollama
AGRIGUARD_LLM_BASE_URL=http://127.0.0.1:11434/v1
AGRIGUARD_LLM_API_KEY=
AGRIGUARD_LLM_MODEL=qwen3:4b-instruct-2507-q4_K_M
AGRIGUARD_LLM_STRUCTURED_MODE=json_schema
```

An explicitly selected DeepSeek, Qwen, or other compatible cloud endpoint uses
the same fields with `AGRIGUARD_LLM_PROVIDER=openai-compatible`, its HTTPS base
URL, API key, and model name. Use `json_object` or `prompt_only` only when that
provider does not support JSON Schema. API keys remain in `.env` and are never
returned to the frontend or written to logs.

Open a MySQL command session as the application user:

```powershell
docker compose --env-file .env -f infra/compose.yaml exec mysql `
  sh -c 'mysql -u"$MYSQL_USER" -p "$MYSQL_DATABASE"'
```

Stop the container without deleting its stored database files:

```powershell
docker compose --env-file .env -f infra/compose.yaml down
```

## Existing model assets

The previously trained IP102 dataset, scripts, weights, and experiment outputs
remain under the local `data/` directory. That directory is ignored by Git to
avoid committing large datasets and binary artifacts. A reproducible manifest
is committed under `model_artifacts/` without modifying the training outputs.

Verify the local weight and fixed smoke images against the committed manifest:

```powershell
Set-Location backend
python scripts/verify_model_artifact.py
```

See `model_artifacts/ip102-yolo26n/MODEL_CARD.md` for metrics, intended use,
per-class weaknesses, and unresolved evaluation risks.
