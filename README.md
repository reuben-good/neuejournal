## NeueJournal
A simple, encrypted, daily journal to run on your own hardware.

### Installation
1. Clone the repository
``` bash
git clone https://github.com/reuben-good/neuejournal.git
cd neuejournal
```
2. Set environment variables
``` bash
cp .env.example .env
```
``` env
DATABASE_NAME=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=my_super_strong_password
POSTGRES_HOST=localhost
POSTGRES_PORT=8080
MASTER_KEY=xxx
```
You can generate the master key with:
``` python
import os
import base64
base64.urlsafe_b64encode(os.urandom(32)).decode()
```
3. Start the containers
``` bash
docker compose up -d
```
This will start both the journal app and a Postgres database. If you already have a database instance, adjust the .env settings to connect to that instead and run:
`docker compose up journal -d`

4. Create an account

Navigate to `localhost:8000` and register. You'll then be presented with the journal screen.

### How encryption works
When a change is made to the [Quill](https://quilljs.com/) editor, a post request is sent to /entry/save/entry_date with the full text. The data is encrypted using the user_key field of each account with AES 256 bit encryption (see apps/helpers/encryption.py). The user_key field is encrypted with the master key set in .env.

### Upcoming features
- Alerts on journal page if a save fails
- Mood tracking
- Journal search
- Mark entries as 'favourite' for easy access.
