# ShelfSense Gateway

The ShelfSense Gateway is the FastAPI service used by the ShelfSense app and Raspberry Pi scanners. It accepts product images and scan data, stores review items in SQLite, exposes the inventory API, and serves a small admin dashboard for reviewing scans.

Image OCR currently uses Google Gemini. Uploaded images are kept on the gateway and are also uploaded to S3 when a working AWS configuration is available; local storage remains the fallback.

## What is in this repository

- `app/` - FastAPI application, database models, repositories, OCR, image handling, and the Raspberry Pi client.
- `app/api/admin.py` - browser dashboard and admin scan endpoints.
- `scripts/pi_push_scan.py` - small Pi script for one-shot, loop, or GPIO-triggered image uploads.
- `raspberry_pi_setup.md` - setup and systemd instructions for the background Pi client.
- `HARDWARE_SETUP_GUIDE.md` - end-to-end hardware and demo setup.
- `test/fixtures/` - sample images for OCR checks.
- `.env.example` - starting point for local configuration.

## Run the gateway locally

Requirements: Python 3.10 or newer.

```bash
python -m venv .venv
```

Activate the environment:

```bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

Install the server dependencies:

```bash
pip install -r requirements.txt
```

`app/requirements.txt` is a larger environment export. Use it instead if you need the full OCR, AWS, and Raspberry Pi toolchain.

Copy the example configuration and set the values you need:

```bash
cp .env.example .env
```

At minimum, make `GEMINI_API_KEY` available to the process. For example:

```bash
# macOS/Linux
export GEMINI_API_KEY="your-key"

# Windows PowerShell
$env:GEMINI_API_KEY = "your-key"
```

The gateway uses SQLite by default and creates the database on startup. To run it:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) for the generated API documentation or [http://localhost:8000/admin](http://localhost:8000/admin) for the review dashboard.

The dashboard defaults are `admin` / `admin123`. Set `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `SECRET_KEY` before using the gateway outside a local demo.

## API surface

All API routes use the `/api/v1` prefix.

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/` | Basic gateway response and links to the dashboard and docs. |
| `GET` | `/api/v1/system/status` | Gateway health response. |
| `POST` | `/api/v1/images/upload` | Store an image and return its image id and URL. |
| `POST` | `/api/v1/scans/from-image` | Upload a front image, optionally a back image, run OCR, and add a pending scan. |
| `POST` | `/api/v1/scans/` | Add a scan from structured JSON. |
| `GET` | `/api/v1/scans/pending` | List scans waiting for review. |
| `POST` | `/api/v1/scans/{id}/approve` | Move a pending scan into inventory. |
| `POST` | `/api/v1/scans/{id}/reject` | Reject a pending scan. |
| `POST` | `/api/v1/scans/{id}/rescan` | Request another scan. |
| `GET`, `POST`, `PUT`, `DELETE` | `/api/v1/products` | Manage inventory products. |
| `GET` | `/api/v1/history` | Read scan history. |

The dashboard also uses `/api/v1/admin/login`, `/api/v1/admin/stats`, `/api/v1/admin/scans`, and `/api/v1/admin/upload-test`.

## Raspberry Pi client

For the full background client, including local retry storage and systemd setup, read [raspberry_pi_setup.md](raspberry_pi_setup.md).

The standalone pusher is useful for a quick hardware test:

```bash
python scripts/pi_push_scan.py \
  --gateway http://<GATEWAY_IP>:8000 \
  --device-id pi-kitchen-01
```

It can also scan continuously or use a GPIO button:

```bash
python scripts/pi_push_scan.py --gateway http://<GATEWAY_IP>:8000 --loop --interval 10
python scripts/pi_push_scan.py --gateway http://<GATEWAY_IP>:8000 --gpio-button 17
```

For the physical wiring, camera setup, and demo checklist, use [HARDWARE_SETUP_GUIDE.md](HARDWARE_SETUP_GUIDE.md).

## Storage

- SQLite defaults to `database/shelfsense.db`.
- Images default to `app/images/` and are served at `/images/{image_id}`.
- If S3 credentials and `S3_BUCKET_NAME` are available, image uploads also receive an S3 presigned URL.
- The database, local uploads, logs, and `.env` are ignored by Git.

## Development notes

The application creates its tables and image directory during startup. There is no migration framework in this repository, so schema changes should be handled deliberately when an existing database is in use.
