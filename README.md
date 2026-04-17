
# NeueJournal

#### A simple, encrypted, self-hostable daily journal

### Table of contents
- [Installation](#installation)
- [Roadmap](#roadmap)

#### About
Built with [Django](https://www.djangoproject.com/) and [PostgreSQL](https://www.postgresql.org/), NeueJournal provides a simple, encrypted daily journal that requires minimal setup. Just point it at a Postgres instance and write away!
## Installation
1. Copy this compose.yaml:
```yaml
services:
    journal:
        image: ghcr.io/reuben-good/neuejournal:latest
        environment:
            - DATABASE_NAME=postgres
            - POSTGRES_USER=postgres
            - POSTGRES_PASSWORD=xxx
            - POSTGRES_HOST=db
            - POSTGRES_PORT=5432
            - MASTER_KEY=xxx
        volumes:
            - .:/app
        ports:
            - "8000:8000"
        depends_on:
            - db
```

2. Replace the POSTGRES_PASSWORD with a more secure password
3. Generate a MASTER_KEY for encryption:
``` python
import os
import base64
base64.urlsafe_b64encode(os.urandom(32)).decode()
```
4. Run the container
```bash
docker compose up -d
```
5. Make and migrate database records
```bash
docker compose exec journal python manage.py makemigrations
docker compose exec journal python manage.py migrate
```

> [!IMPORTANT]
> You may have issues with the database connection. Ensure if you are using the name of a container that you use the default Postgres port (5432) as the Docker network will not have the same mappings. When using an external db instance, this shouldn't be an issue if the host is set properly.

You can see an example of a working compose file in `compose.yaml` inside this repo.
## Roadmap

- Alerts on journal page if a save fails
- Mood tracking
- Journal search
- Mark entries as 'favourite' for easy access.
- Embeddings for search

### Whole 'Neue-' features
1. Improve and extend neue_accounts to provide an OAuth endpoint so all Neue apps can be accessed with one account & provide other self hosted apps access to this provider to allow one account for all services a user may run
2. Connect 'Neue-' apps together to allow stats/monitoring of both user actions and application state across services. E.g. a neuehabbits app may connect to the journal and automatically mark a "write today's journal entry" habit as completed when a user completes this task.
