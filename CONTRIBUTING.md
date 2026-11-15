# Contributing

Follow the README team setup. Work on a feature branch and open a pull request for review. Include the behavior changed, API compatibility implications, and actual test results. Run `.\.venv\Scripts\python.exe -m pytest -q` before proposing backend changes. Live tests require explicit opt-in and a running local server.

The previous frontend has been removed. A replacement will be integrated separately using the existing API contract. Backend routes, schemas and services belong in backend/app/; scientific transformations belong in pipeline/. OpenAPI at /docs is the current API contract. Coordinate contract changes with both teams. Keep hotspot detections distinct from wildfire incidents, missing observations distinct from zero activity, and native sensor confidence intact.

Keep credentials in local .env or environment variables. Do not upload datasets, generated analytics, local tools, or environments. Review `git status` and `git diff --cached` before every commit. Do not commit synthetic activity as production observations.
