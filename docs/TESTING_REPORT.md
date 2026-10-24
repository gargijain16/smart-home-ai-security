# Testing report (real results from the authoring sandbox, 2026-10-21)
Sandbox limits: Python 3.12, scikit-learn 1.8.0, pandas 3.0.2; **no network**, so FastAPI, pydantic, httpx, npm packages and a browser were unavailable.

| Check | Command | Result |
|---|---|---|
| Backend syntax | `python -m py_compile` on app, tests, scripts | OK |
| Unit tests (ML service, simulator, store) | `python -m unittest discover -s tests -t .` | **18 passed** |
| API integration tests (`tests/test_api.py`, 8 tests) | same command | **Skipped, not run** (fastapi not installed) |
| Notebook, smoke mode, headless execution | `scripts/run_notebook_headless.py` | Ran end-to-end; produced all 6 required artefacts plus a ZIP |
| Notebook, real mode | n/a | **Not run** (dataset not available offline) |
| Frontend TypeScript | `tsc --ignoreConfig --noEmit ...` without installed packages | No syntax errors. 855 errors, all from missing `@types/react`, `vite/client`, etc. Real type-check **not done** |
| Frontend tests / production build | `npm test`, `npm run build` | **Not run** |

What the 18 passing tests cover: demo-mode status without a model; corrupt metadata does not crash; model loads and is flagged synthetic; metadata has schema/provenance; prediction shape, version and timestamp; rejection of missing, unexpected, non-numeric, infinite and empty input; reporting of missing cells; enforced column order; metrics read from saved files; simulator determinism, scenario coverage, rule thresholds and simulated labelling; store lifecycle, filters, pagination, search, status updates, device stats.
Needs real artefacts: any benchmark claim (real dataset + Colab run). Needs packages: `tests/test_api.py` (`pip install -r backend/requirements.txt`), frontend tests/build (`npm install`).
**First thing to do on your machine:** run `python -m unittest discover -s tests -t . -v` (expect 26 tests, 0 skipped) and `cd frontend && npm install && npm run typecheck && npm run build`, and fix anything they surface.
