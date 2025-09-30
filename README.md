# SnippetBox - Online Code Snippet Service

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Tests](https://img.shields.io/badge/tests-20%20passed-brightgreen.svg)

RESTful API service for managing code snippets with full-text search, tagging, and rate limiting.

## Features

- ✅ Create/Read/Update/Delete code snippets
- ✅ Full-text search on title and content
- ✅ Tag-based filtering
- ✅ Pagination support
- ✅ Idempotent creation
- ✅ Rate limiting (60 writes/min per IP)
- ✅ Soft deletion
- ✅ Structured logging with trace IDs
- ✅ Health check endpoint
- ✅ Input validation & SQL injection prevention
- ✅ Configurable CORS

## Quick Start

### Prerequisites
- Python 3.11+
- pip

### Installation

```powershell
# Clone repository
git clone <repository-url>
cd SnippetBox/copilot_claude

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
copy .env.sample .env

# Initialize database
python scripts\init_db.py

# Run server
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

Server will be available at `http://localhost:8000`

### Using Docker

```powershell
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Running Tests

```powershell
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_api.py -v
```

## API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Load Testing

```powershell
# Run load test (100 concurrent users, 30 seconds)
locust -f scripts/load_test.py --host=http://localhost:8000 --users=100 --spawn-rate=10 --run-time=30s --headless
```

## Environment Variables

See `.env.sample` for all configuration options.

## Project Structure

```
copilot_claude/
├── src/                    # Source code
│   ├── main.py            # FastAPI app entry
│   ├── config.py          # Configuration
│   ├── database.py        # Database setup
│   ├── models.py          # SQLAlchemy models
│   ├── schemas.py         # Pydantic schemas
│   ├── crud.py            # CRUD operations
│   ├── middleware.py      # Logging & rate limiting
│   └── utils.py           # Utilities
├── tests/                 # Test suite
├── scripts/               # Utility scripts
├── migrations/            # Database migrations
└── requirements.txt       # Python dependencies
```

## License

MIT
