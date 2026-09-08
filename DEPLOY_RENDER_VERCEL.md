# CargoCast — Render + Vercel Deployment

This package keeps the original Stitch-style HTML frontend and moves the Python API to Render.

## 1. Push the updated files to GitHub

Replace/add these files from this ZIP in the GitHub repository:

- `backend/main.py`
- `backend/requirements.txt`
- `.python-version`
- `frontend/index.html`
- `frontend/dashboard.html`
- `frontend/forecast.html`
- `frontend/scenarios.html`

The three HTML pages currently contain this placeholder API URL:

`https://YOUR-RENDER-SERVICE.onrender.com`

After Render creates your service, replace that placeholder with the exact Render URL in all three HTML files.

## 2. Deploy the API to Render

Create a **Web Service** connected to the GitHub repository.

Recommended settings:

- Branch: `main`
- Root Directory: leave blank / repository root
- Runtime: `Python 3`
- Build Command: `pip install -r backend/requirements.txt`
- Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

The repository root `.python-version` pins Python to 3.12.

After deployment, test:

- `/api/health`
- `/api/forecast?horizon_days=60`
- `/api/recommendation?horizon_days=60`
- `/docs`

## 3. Connect the frontend to Render

Copy the Render service URL, for example:

`https://cargocast-api-xxxx.onrender.com`

In each of these files:

- `frontend/dashboard.html`
- `frontend/forecast.html`
- `frontend/scenarios.html`

replace:

`https://YOUR-RENDER-SERVICE.onrender.com`

with your actual Render URL.

Commit and push the change to GitHub.

## 4. Deploy the frontend to Vercel

Import the same GitHub repository into Vercel.

Use:

- Framework Preset: `Other`
- Root Directory: `frontend`
- Build Command: leave empty
- Output Directory: leave empty
- Install Command: leave empty

Deploy.

Vercel will serve the original HTML pages directly.

## 5. Open CargoCast

Open the Vercel deployment URL. `frontend/index.html` redirects to `dashboard.html`.

The browser flow is:

Vercel → original Stitch HTML/JavaScript → Render FastAPI → `backend/pipeline.py`

## Important note about the model

The uploaded original repository does not contain the `models/`, `nlp/`, or `decision_engine/` directories expected by `backend/pipeline.py`. The backend therefore uses the documented fallback/mock implementations currently present in `backend/pipeline.py`.

The deployment architecture is ready for those real modules to be added later without changing the frontend API contract.
