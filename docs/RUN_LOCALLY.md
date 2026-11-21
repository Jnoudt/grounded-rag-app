# Run locally

## Backend

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt

$env:RAG_OFFLINE_MODE = "true"
func start
```

The API runs at `http://localhost:7071/api`. Azure Functions Core Tools must be
installed.

## Frontend

In a separate terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite development server proxies `/api` to
port `7071`. Enter a Function key only for the current browser session when
needed. If the API is unreachable, the console clearly switches to a local
offline fallback.

## Tests and quality

```powershell
pytest
ruff check src function_app.py tests
mypy src function_app.py
bandit -q -r src function_app.py
pip-audit -r requirements.txt

cd frontend
npm run lint
npm run build
npm run audit
```

## Live Azure mode

Set `RAG_OFFLINE_MODE=false` and provide the infrastructure-aligned values from
`.env.example`, including `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_INDEX_NAME`,
`AZURE_AI_ENDPOINT`, `AZURE_AI_CHAT_DEPLOYMENT`, and
`AZURE_OPENAI_API_VERSION`. Authenticate with Azure CLI or a workload identity
that has the Terraform-created managed identity and least-privilege roles.
