# Deployment
## Why a localhost backend cannot serve a public site
A Vercel page runs in the *visitor's* browser. `http://localhost:8000` there means the visitor's own machine, not your laptop. Judges need a **public HTTPS backend URL**. Options: deploy the backend (below), or for a live demo tunnel your laptop (`cloudflared tunnel --url http://localhost:8000`) and put that URL in Vercel and `CORS_ORIGINS`.

## Backend (any Python host: Render, Railway, Fly.io, a VPS)
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1` from `backend/` (one worker: simulator state is in-process).
- Install: `pip install -r requirements.txt`; pin `scikit-learn` to the version in `model_metadata.json`.
- Health check: `GET /api/health`.
- Env: `CORS_ORIGINS=https://your-app.vercel.app` (explicit, no `*`; credentials are disabled), `DB_PATH=:memory:` on ephemeral disks (SQLite files are lost on redeploy; use a persistent disk if you need history), `MODELS_DIR`, `REPORTS_DIR`.
- Model files: a Random Forest `.joblib` here is a few MB (check size; most Git hosts cap files at 100 MB). Commit `models/` and `reports/` for the deploy branch, use Git LFS, or mount a disk. Remove them from `.gitignore` only on a deploy branch. Not suited to serverless functions (package size, cold start, in-process state).
- `render.yaml` is provided as an example blueprint.

## Frontend on Vercel
1. Push the repo to GitHub.
2. Vercel → Add New → Project → import it; **Root Directory: `frontend`**; framework Vite (auto); build `npm run build`; output `dist`.
3. Settings → Environment Variables: `VITE_API_BASE_URL = https://<your-backend-host>` (no trailing slash) for Production (and Preview).
4. Deploy. Then add the resulting Vercel URL to the backend's `CORS_ORIGINS` and restart it.
5. Redeploy after changes: `git push`. Changing an env var requires a redeploy (it is baked in at build time).
If the variable is missing or the API is down, the app shows a "Backend not reachable" card with the reason; it never falls back to `localhost` and never fabricates data.
