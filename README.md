# Image Processing Service

A FastAPI service for effective image management and processing. It allows users to upload and read images and their thumbnails. The API stores the original, responds immediately, and a worker generates thumbnails afterwards.

## Features

- File upload and management : upload JPEG, PNG and WebP images with strict validation (real image check, size and dimension limits)
- Effective file processing: background thumbnail generation (128, 256 and 512 px, WebP) with Celery
- Read endpoints for images, thumbnails, and thumbnail feed
- Files on local disk behind a small storage abstraction, ready to swap for S3
- Database migrations with Alembic
- One-command setup with Docker Compose

## Tech stack

| Area | Tool |
|---|---|
| API | FastAPI, Pydantic v2, pydantic-settings |
| Background jobs | Celery, Redis (broker and result backend) |
| Database | PostgreSQL (`pgvector/pgvector:pg17` image), SQLAlchemy 2.0, Alembic, psycopg 3 |
| Image processing | Pillow |
| Monitoring | Flower |
| Packaging | uv, Docker, Docker Compose |

## How it works

```
Client ──POST /images──▶ API ──1. validate (Pillow)
                          │    2. save original to storage
                          │    3. insert row in Postgres
                          │    4. enqueue process_image(image_id)
                          ▼
                    201 {image_id}                 Redis (broker)
                                                       │
                                                       ▼
                                                Celery worker
                                                  load image row
                                                  create thumbnails (Pillow)
                                                  save files + upsert rows
```

1. **Upload**: the API validates the file, saves it under a key it generates itself, creates the `images` row, enqueues a Celery task with only the image id, and returns `201 Created`.
2. **Processing**: the worker opens its own database session, creates the thumbnails, saves them to storage, and upserts `image_thumbnails` rows.
3. **Reading**: clients fetch metadata as JSON and files by URL. An image without thumbnails simply has an empty list, meaning "not ready yet".

Users never see Celery task state. Developers watch tasks, failures and retries in Flower.

## Getting started

### Prerequisites

- Docker with Docker Compose (a recent Docker Engine, 25 or newer, because the compose file uses `start_interval` in healthchecks)
- [uv](https://docs.astral.sh/uv/) for working on the code outside Docker
- The Python version is pinned in `.python-version`

### Configure

Create a `.env` file in the project root:

```env
POSTGRES_USER=app
POSTGRES_PASSWORD=change-me
POSTGRES_DB=img_processing
DATABASE_URL=postgresql+psycopg://app:change-me@db:5432/img_processing

FLOWER_USER=admin
FLOWER_PASSWORD=change-me
```

Notes:

- `DATABASE_URL` in `.env` is the URL the **containers** use, so its host is the Compose service name `db`.
- Avoid `$` in values, because Compose treats it as a variable reference.
- The `POSTGRES_*` values are read only when the database volume is first created.

### Run

```bash
docker compose up -d --build
```

This builds the image and starts everything.

| Service | URL |
|---|---|
| API docs (Swagger UI) | http://localhost:8000/docs |
| Flower | http://localhost:5555 (basic auth from `FLOWER_USER` and `FLOWER_PASSWORD`) |
| PostgreSQL from your machine | `localhost:5433` |

### Try it

```bash
# upload
curl -F "file=@photo.jpg" http://localhost:8000/images/

# list images (paginated)
curl "http://localhost:8000/images/?limit=10&offset=0"

# thumbnails of one image (empty list until the worker has finished)
curl http://localhost:8000/images/<image_id>/thumbnails

# download a 128 px thumbnail
curl "http://localhost:8000/images/<image_id>/thumbnail?size=128" -o thumb.webp
```

**Using thumbnails in a client**: fetch a JSON list (feed or per-image list), then put each `url` into an `<img>` tag. The browser downloads, caches and lazy-loads the files itself.

```html
<img src="/images/<image_id>/thumbnail?size=128" width="64" height="64"
     style="object-fit: cover; border-radius: 50%" loading="lazy">
```

## Project structure

```
src/
  main.py                   FastAPI application
  config.py                 settings (pydantic-settings)
  celery_app.py             Celery instance
  celery_tasks.py           process_image task
  storage.py                LocalStorage and get_storage()
  thumbnails.py             thumbnail generation with Pillow
  api/                      routers, schemas, dependencies
  services/                 image service, upload validation
  db/
    models/image_models.py  Image, ImageThumbnail
    repositories/           sync repository (writes) and async repository (reads)
alembic/                    migrations
docker-compose.yml
Dockerfile
```

## Configuration

| Variable | Used by | Description |
|---|---|---|
| `DATABASE_URL` | api, worker, migrate | SQLAlchemy URL. Host `db` inside Compose, `localhost:5433` from your machine |
| `UPLOAD_DIR` | api, worker | Root folder of the file storage (`/data/uploads` in Docker). The API and worker must share it |
| `CELERY_BROKER_URL` | api, worker, flower | Redis broker, for example `redis://redis:6379/0` |
| `CELERY_RESULT_BACKEND` | api, worker | Redis result backend, for example `redis://redis:6379/1` |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | db | Database credentials, applied only on first start |
| `FLOWER_USER`, `FLOWER_PASSWORD` | flower | Basic auth for the Flower dashboard |


## Development

### Rebuilding after changes

```bash
docker compose up -d --build            # code or dependency changes
docker compose up -d --build api worker # only the services that run your code
docker compose up -d                    # changed .env values (recreates the affected containers)
docker compose logs -f worker           # follow worker logs
```

- The code is copied into the image at build time, so edits on your machine need `--build`. The API and the worker are separate containers, so rebuild both after changing task code.
- `docker compose restart` does **not** pick up `.env` changes. Recreate with `up -d`.
- Celery does not auto-reload. For a faster loop, bind-mount `./src` in a `docker-compose.override.yml`, run uvicorn with `--reload`, and restart the worker manually.

### Migrations

Generate migrations on your machine against the running database (note the host URL, `localhost:5433`), then review the file in `alembic/versions/`:

```bash
docker compose up -d db

DATABASE_URL="postgresql+psycopg://app:change-me@localhost:5433/img_processing" \
  uv run alembic revision --autogenerate -m "describe the change"

DATABASE_URL="postgresql+psycopg://app:change-me@localhost:5433/img_processing" \
  uv run alembic upgrade head
```

### Dependencies

```bash
uv add <package>          # then rebuild the image
uv sync                   # install from uv.lock
uv tree                   # inspect the dependency tree
```

### Monitoring

Open Flower at http://localhost:5555 to see workers, queued, succeeded and failed tasks, and retries. Task states appear when workers publish events (the `-E` worker flag).
