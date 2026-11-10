# Setup

[Back to overview](index.html)

Requirements: Python 3.11+, Docker, [ast-grep](https://github.com/ast-grep/ast-grep/releases), a Gemini API key and a GitHub token.

```bash
git clone https://github.com/The-Harsh-Vardhan/CASCADE
cd CASCADE
pip install -e ".[dev]"
playwright install chromium

cp .env.example .env     # set GEMINI_API_KEY_1, GITHUB_TOKEN, DOCUMENSO_EMAIL,
                         # DOCUMENSO_PASSWORD, NEO4J_PASSWORD
docker compose up -d     # Neo4j on :7474 / :7687
git clone https://github.com/documenso/documenso data/repos/documenso
python scripts/validate_env.py
```

## Build the graph (one time)

```bash
python scripts/run_pipeline.py --phase 1   # crawl
python scripts/run_pipeline.py --phase 2   # ingest requirements
python scripts/run_pipeline.py --phase 3   # index code
python pipeline/offline.py                 # Phase 4 + seed flows and API endpoints
```

## Analyze a PR

```bash
python run.py https://github.com/documenso/documenso/pull/3046
```

Reports are written to `outputs/reports/pr_3046/` as Markdown, HTML, PDF and DOCX.

## Notes

- `CRAWL_USE_FIXTURE=true` reads `data/crawl/fixtures/*.json`; that directory is not committed, so you must supply your own snapshots.
- Unit tests: `pytest tests/unit/`.
- Troubleshooting table: see the [README](https://github.com/The-Harsh-Vardhan/CASCADE#troubleshooting).
