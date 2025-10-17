# Acme Dataroom Backend

Flask service that powers the data room APIs.

## Setup

```bash
pip install -r requirements.txt
FLASK_APP=app.main:app FLASK_RUN_PORT=8000 flask run --debug
```

The server uses SQLite (`dataroom.db`) for metadata and stores uploaded PDFs in `storage/`.

## Tests

Run the Flask integration tests with pytest:

```bash
pytest
```

## Mock Data

Seed the local database with an example folder hierarchy and placeholder PDFs. You can safely run the command multiple times without creating duplicates.

```bash
python -m app.mock_data
```
