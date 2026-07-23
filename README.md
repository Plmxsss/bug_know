# AgriGuard AI

AgriGuard AI is a learning-driven agricultural pest detection and knowledge
question-answering project. The finished system will connect a trained IP102
YOLO model, FastAPI, MySQL, Qdrant RAG, local or API-hosted language models,
and a Vue 3 frontend.

The repository is built in small, verifiable stages. The current stage can
validate and store an uploaded image, run the trained IP102 YOLO model on GPU,
draw an annotated result, and persist the task and bounding boxes in MySQL.
RAG, LLM integration, and the frontend remain in progress.

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

Start MySQL from the repository root:

```powershell
docker compose --env-file .env -f infra/compose.yaml up -d mysql
docker compose --env-file .env -f infra/compose.yaml ps
```

The Compose port mapping makes the MySQL process inside the container available
to the locally running FastAPI process at `127.0.0.1:3306`. After starting both
MySQL and FastAPI, verify the real database connection:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/ready
```

Expected response:

```json
{
  "status": "ready",
  "database": "ok"
}
```

This endpoint executes `SELECT 1`. It returns HTTP 503 when MySQL cannot be
reached, while `/api/v1/health` continues to report whether FastAPI itself is
running.

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
