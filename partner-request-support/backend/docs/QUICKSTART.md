# Backend quickstart

The maintained setup/configuration instructions are in the [backend README](../README.md). This short entry replaces earlier commands and deployment assumptions.

From `partner-request-support/backend/`, with Python 3.13 available:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Configure Supabase, OpenAI, AWS, and the target CLARISA URLs as described in the README before starting. Client construction during import can fail with missing configuration. Provisioning SQL or synchronizing catalogs changes database contents; it is not part of a read-only startup check.

```bash
python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

```bash
curl http://localhost:8000/health
```

Health is process-only. See the [API guide](../../docs/API_GUIDE.md) before processing data: spreadsheet creation defaults true, processing synchronizes/deletes obsolete catalog rows, and cache/model/email operations may occur. Do not use live example scripts as an isolated regression suite.

See [branch differences](../../docs/BRANCH_DIFFERENCES.md) before service-main integration. The local entry point is `api:app`; Lambda uses `main.handler`. Docker installs `requirements.txt`.
