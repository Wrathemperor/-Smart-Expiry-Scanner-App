# ShelfSense — Smart Expiry Scanner & Inventory Gateway Server

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%2B-red.svg)](https://www.sqlalchemy.org/)
[![Google Gemini](https://img.shields.io/badge/AI-Google%20Gemini%20Vision-orange.svg?logo=google)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**ShelfSense Gateway Server** is a high-performance FastAPI backend designed for automated pantry and grocery expiry tracking. It orchestrates multi-modal edge and mobile clients, processes food packaging imagery through advanced Vision AI models (Google Gemini Vision and AWS Bedrock Nova Lite), enforces strict temporal grounding to disambiguate expiry dates, and manages inventory, pending review queues, and scan histories.

---

## Architecture Overview

```
                                +---------------------------+
                                |  ShelfSense Android App   |
                                +-------------+-------------+
                                              |  HTTP / REST
                                              v
+-----------------------+       +-------------+-------------+       +------------------------+
|  Raspberry Pi Client  | ----> |   ShelfSense Gateway      | ----> |  Google Gemini Vision  |
|  (USB/Pi Cam + ZBar)  |       |   (FastAPI Backend)       |       |  (or AWS Bedrock Nova) |
+-----------------------+       +-------------+-------------+       +------------------------+
                                              |
                                              +----> SQLite Database (`database/shelfsense.db`)
                                              +----> Local / S3 Image Storage
```

---

## Key Features

- **Multi-Modal Vision AI Extraction**:
  - Dynamically discovers and auto-ranks Google Gemini Vision models (`gemini-2.5-flash`, `gemini-2.0-flash`, `gemini-1.5-flash`, etc.).
  - Automatic failover and 60-second cooldown on HTTP 429/503 errors.
  - Multi-provider support with fallback to **AWS Bedrock Nova Lite**.
- **Temporal Grounding & Date Normalization**:
  - Injects dynamic anchor dates (`todayIso`) to prevent historical year hallucinations.
  - Automatically parses missing-year dates (`"18 OCT"`) and 2-digit years (`"'26'"` -> `"2026"`).
  - Normalizes product categories into standardized catalogs (`Dairy`, `Produce`, `Meat`, `Pantry`, `Beverages`, `Pharmacy`, `Prepared Meals`, `Bakery`, `Other`).
- **Edge Client Integration (Raspberry Pi)**:
  - Automated continuous scanning with OpenCV camera capture and ZBar barcode decoding.
  - Offline scan queue with automatic sync upon network reconnection.
- **Dual Queue Scanning System**:
  - Direct scan ingestion for fully automated workflows.
  - Pending review queue with approval/rejection endpoints for administrative control.
- **Structured Data Persistence**:
  - Relational persistence powered by SQLAlchemy 2.0 with SQLite.
  - Dedicated repositories and models for products, scan history, and pending scans.

---

## Project Structure

```
gateway-server/
├── app/
│   ├── api/                    # FastAPI route controllers
│   │   ├── history.py          # Scan history endpoints
│   │   ├── images.py           # Image upload and serving
│   │   ├── notification.py     # Expiry notification endpoints
│   │   ├── pending_scans.py    # Pending review queue endpoints
│   │   ├── products.py         # Inventory product CRUD
│   │   ├── scans.py            # Automated scan ingestion
│   │   └── system.py           # Gateway status & health checks
│   ├── core/                   # Core configuration and enums
│   │   ├── config.py           # Pydantic environment settings
│   │   ├── enums.py            # Enumeration types
│   │   └── loggin.py           # Logging configuration
│   ├── database/               # Database engine and sessions
│   │   ├── base.py             # Declarative base
│   │   ├── database.py         # Table creation helpers
│   │   ├── dependencies.py     # FastAPI db session dependencies
│   │   └── session.py          # SQLAlchemy session maker
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── pending_scan.py     # Pending scan entity
│   │   ├── products.py         # Product entity
│   │   └── scan_history.py     # Scan history log entity
│   ├── repositories/           # Data access layer
│   ├── schemas/                # Pydantic request/response schemas
│   ├── services/               # Business logic & AI services
│   │   ├── image_service.py    # Image storage & resizing
│   │   ├── ocr_service.py      # Gemini Vision & OCR extraction
│   │   ├── product_services.py # Product business logic
│   │   └── scan_service.py     # Scan processing logic
│   ├── main.py                 # FastAPI application entrypoint
│   ├── check_pi_dependencies.py# Raspberry Pi system health validator
│   ├── raspberry_pi_client.py  # Daemon client for Raspberry Pi hardware
│   └── test_bedrock.py         # AWS Bedrock integration test
├── test/
│   └── fixtures/               # Test images for OCR validation
├── .env.example                # Sample environment configuration
├── .gitignore                  # Git ignore rules
├── currentChanges.md           # Implementation change log
├── raspberry_pi_setup.md       # Comprehensive Raspberry Pi setup guide
└── requirements.txt            # Python dependencies
```

---

## Getting Started

### 1. Prerequisites
- **Python 3.10+**
- **pip** package manager
- (Optional) Google Gemini API Key or AWS credentials with Bedrock access.

### 2. Installation

Clone the repository and navigate into the project directory:

```bash
git clone https://github.com/Wrathemperor/-Smart-Expiry-Scanner-App.git
cd -Smart-Expiry-Scanner-App
```

Create and activate a virtual environment:

```bash
# On Linux/macOS
python3 -m venv venv
source venv/bin/activate

# On Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` to configure your API keys and provider:

```env
# Google Gemini Vision API Key (recommended)
GEMINI_API_KEY=your_gemini_api_key_here

# OCR Provider: 'gemini' or 'bedrock'
OCR_PROVIDER=gemini

# AWS Bedrock Configuration (if OCR_PROVIDER=bedrock)
AWS_REGION=ap-south-1
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0

# Database Configuration
DATABASE_URL=sqlite:///./database/shelfsense.db
```

### 4. Running the Server

Start the FastAPI gateway using Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The server will initialize the SQLite database automatically on startup and will be accessible at `http://localhost:8000`.

---

## Interactive API Documentation

Once running, interactive documentation is available directly in your browser:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## API Endpoints Reference

| Category | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **System** | `GET` | `/` | Health check confirmation |
| | `GET` | `/api/v1/system/status` | Gateway and Pi connection health |
| **Products** | `GET` | `/api/v1/products/` | List all pantry inventory items |
| | `POST` | `/api/v1/products/` | Create a new product record |
| | `GET` | `/api/v1/products/{id}` | Retrieve specific product details |
| | `PUT` | `/api/v1/products/{id}` | Update product details |
| | `DELETE` | `/api/v1/products/{id}` | Delete a product from inventory |
| **Images** | `POST` | `/api/v1/images/upload` | Upload food packaging image |
| | `GET` | `/api/v1/images/{filename}` | Retrieve uploaded packaging image |
| **Scans** | `POST` | `/api/v1/scans/` | Ingest scan payload from Pi or app |
| **Pending Scans** | `GET` | `/api/v1/pending-scans/` | List scans waiting for manual review |
| | `POST` | `/api/v1/pending-scans/` | Submit item to pending queue |
| | `POST` | `/api/v1/pending-scans/{id}/approve` | Approve scan and insert into inventory |
| | `POST` | `/api/v1/pending-scans/{id}/reject` | Reject and dismiss pending scan |
| **History** | `GET` | `/api/v1/history/` | View historical scan and action logs |

---

## Raspberry Pi Edge Scanner

To deploy an edge camera scanner on a Raspberry Pi:

1. Refer to [raspberry_pi_setup.md](raspberry_pi_setup.md) for full hardware, dependency, and systemd service instructions.
2. Validate system dependencies:
   ```bash
   python -m app.check_pi_dependencies
   ```
3. Run the client daemon:
   ```bash
   python -m app.raspberry_pi_client --gateway http://<GATEWAY_IP>:8000 --device-id pi-kitchen-01 --interval 30
   ```

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
