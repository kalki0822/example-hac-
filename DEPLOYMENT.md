# Production Deployment Guide
**Vitals — Hospital Readmission Risk Decision Support Platform**

## Local Development Deployment
```bash
# 1. Install Backend Dependencies
pip install -r requirements.txt

# 2. Run Backend Service (Port 8000)
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# 3. Run Frontend Service (Port 5173)
cd frontend
npm install
npx vite --host --port 5173
```

## Docker Compose Deployment
```bash
docker-compose up --build
```

## Demo Accounts
- **Clinician**: `clinician@vitals.health` / `Clinician123!`
- **Analyst**: `analyst@vitals.health` / `Analyst123!`
- **Admin**: `admin@vitals.health` / `Admin123!`
