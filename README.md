# NeueJournal

#### A simple, encrypted, self-hostable daily journal

### Table of contents
- [Installation](#installation)
- [Roadmap](#roadmap)

#### About
Built with [Django](https://www.djangoproject.com/), NeueJournal provides a simple, encrypted daily journal that requires minimal setup. Just point it at a Postgres instance and write away!

## Installation

### Prerequisites
- [Docker](https://docs.docker.com/engine/install/) and [Docker Compose](https://docs.docker.com/compose/install/) (V2 plugin, invoked as `docker compose`)
- An S3-compatible object store (a local [Garage](https://garagehq.deuxfleurs.fr/) instance is included by default for media/file storage)
- An instance of [PostgreSQL](https://www.postgresql.org/)

### 1. Clone the repository
```bash
git clone https://github.com/reuben-good/neuejournal.git
cd neuejournal
```

### 2. Configure environment variables
Copy the example environment file and edit it:
```bash
cp .env.example .env
```

At minimum, set these values in `.env`:

| Variable            | Description                                                                  |
|---------------------|------------------------------------------------------------------------------|
| `POSTGRES_PASSWORD` | A strong password for the local Postgres database.                           |
| `MASTER_KEY`        | A base64url-encoded 32-byte secret used for journal entry encryption.        |
| `GARAGE_ACCESS_KEY` | An access key for the Garage S3-compatible storage backend.                  |
| `GARAGE_SECRET_KEY` | A secret key for the Garage S3-compatible storage backend.                   |
| `GARAGE_BUCKET`     | A bucket name for the Garage S3-compatible storage backend.                  |
| `GARAGE_ENDPOINT_URL`     | The URL your Garage instance can be found at.                  |
| `DJANGO_SECRET_KEY` | A Django secret key used for cryptographic signing (e.g. session cookies).   |

**Generating a `MASTER_KEY`:**
```python
python -c "import os, base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

**Generating a `DJANGO_SECRET_KEY`:**
```python
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 3. Create the Garage configuration
The included `garage.toml` file configures the local S3-compatible storage. An example can be found here:
```toml
metadata_dir = "/var/lib/garage/meta"
data_dir = "/var/lib/garage/data"
db_engine = "lmdb"
block_size = 1048576

replication_mode = "none"

rpc_bind_addr = "[::]:3901"
rpc_public_addr = "127.0.0.1:3901"
rpc_secret = "changeme"

[s3_api]
s3_region = "garage"
api_bind_addr = "[::]:3900"

[admin]
api_bind_addr = "[::]:3903"
admin_token = "changeme"
```

> You can change the `rpc_secret` and `admin_token` values, but they are only used for internal communication between Garage services and are not exposed externally.

### 4. Start all services
```bash
docker compose up -d
```

This starts the following containers:
- `db` — PostgreSQL database
- `redis` — Message broker for Celery task queue
- `garage` — Local S3-compatible object storage
- `journal` — The Django application (served on port 8000)
- `celery-worker` — Handles background tasks (e.g. file processing)
- `celery-beat` — Scheduled task scheduler

### 5. Apply database migrations
```bash
docker compose exec journal python manage.py migrate
```

> `makemigrations` is **not** needed here — the published image already includes all migration files. You only need `makemigrations` if you are developing and have modified the models.

### 6. Access the journal
Open [http://localhost:8000](http://localhost:8000) in your browser and register an account.

## Adding stickers
Create a superuser with:
```bash 
docker compose exec journal python manage.py createsuperuser
```
Then access Django's admin dashboard at [http://localhost:8000/admin](http://localhost:8000/admin) and login with the credentials you just created.
Create a sticker pack, add stickers then assign it to a user in the Owned packs section. 

## Updating
```bash
docker compose pull
docker compose up -d
docker compose exec journal python manage.py migrate
```

> [!IMPORTANT]
> - The compose file maps the PostgreSQL container port `5432` to the host port configured in `POSTGRES_PORT` (default: `5432`). If that port is already in use, change `POSTGRES_PORT` in your `.env` file.
> - For production, consider pointing at an external managed Postgres instance and S3-compatible store instead of the local containers. Update `POSTGRES_HOST`, `GARAGE_*`, and any other relevant variables in `.env` accordingly.

You can see a fully working compose file in `compose.yaml` inside this repo.

## Roadmap

- Different types of journal (i.e. travel journals let you create a map of different places you visit, add photos with tagged locations etc)
- Customisable journal pages (add your own text fields, images, tables etc - a Notion-esque setup in the journal interface)

### Whole 'Neue-' features
1. Improve and extend neue_accounts to provide an OAuth endpoint so all Neue apps can be accessed with one account & provide other self hosted apps access to this provider to allow one account for all services a user may run
2. Connect 'Neue-' apps together to allow stats/monitoring of both user actions and application state across services. E.g. a neuehabbits app may connect to the journal and automatically mark a "write today's journal entry" habit as completed when a user completes this task.
