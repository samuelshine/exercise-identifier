# Backend — Exercise Identifier

FastAPI service for the Exercise Identifier MVP.

## Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run (dev)

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Then hit:
- http://localhost:8000/        → `{"message": "Hello World"}`
- http://localhost:8000/health  → `{"status": "ok"}`
- http://localhost:8000/docs    → auto-generated Swagger UI
