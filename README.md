# Grounded RAG + Automated Evaluation

A citation-grounded retrieval-augmented generation system built with Python 3.12,
Azure Functions v2, Pydantic v2, Azure AI Search, Azure AI Services, and a
React + TypeScript provenance console.

## Architecture

- `src/rag/chunker.py`: deterministic chunks using
  `{doc_slug}_p{page}_c{idx}`, page, section, and character offsets.
- `src/rag/retriever.py`: deterministic offline corpus or Azure AI Search using
  `DefaultAzureCredential`.
- `src/rag/generator.py`: prompt-injection-hardened live Azure OpenAI path and
  deterministic offline mock; every claim passes `CitationGroundingVerifier`.
- `src/eval/harness.py`: golden answerable and negative-control cases with
  retrieval recall, citation validity, abstention accuracy, latency, and
  estimated token/cost metrics.
- `function_app.py`: function-key-protected `/api/health`, `/api/query`,
  `/api/eval/run`, and `/api/eval/latest` endpoints.
- `frontend/`: React + TypeScript Enterprise Audit and Provenance console.

## Provenance and abstention

Each chunk has a stable ID, document slug, page number, section, character
offset range, and text. The generator emits claims with chunk IDs and cited
spans. The verifier rejects unknown chunk IDs, weak relevance, or weak lexical
support and returns an explicit abstention. No unverified claim is promoted to
the response.

## Prompt-injection defense

Retrieved text is delimited by `UNTRUSTED_DOCUMENT_CONTEXT_BEGIN/END`, wrapped
inside prompt boundaries, and treated as data rather than instructions.
Authorization headers, bearer tokens, API keys, tokens, secrets, and passwords
are redacted from context. API responses and logs avoid raw SDK or stack-trace
details.

## Infrastructure contract

Use the names in `.env.example`; they align with Terraform outputs from
`grounded-rag-infra`. The storage containers are `documents` and `evaluations`;
Cosmos DB uses database `grounded-rag` and container `evaluation-results`.
Azure data-plane authentication uses `DefaultAzureCredential`. There are no
hardcoded keys or credentials.

## Evaluation metrics

The golden dataset in `data/golden_rag_cases.json` includes answerable and
out-of-scope cases. Retrieval recall measures expected chunk coverage. Citation
validity requires every cited ID to belong to retrieved evidence. Abstention
accuracy compares abstention decisions with golden labels. Latency is measured
with `time.perf_counter()`. Token and cost fields are estimates and offline cost
is zero.

## ADRs

1. **Deterministic IDs**: chunk IDs are derived from normalized document slug,
   page, and chunk index to make provenance reproducible.
2. **Lexical verifier plus model thresholds**: deterministic checks provide a
   fail-closed boundary even when live generation is enabled.
3. **Offline-first execution**: a deterministic corpus and mock generator allow
   all primary workflows to run without cloud credentials or spend.
4. **Session-only key**: the React console stores the Function key only in React
   memory and never in browser storage or source bundles.

## Local run

See [docs/RUN_LOCALLY.md](docs/RUN_LOCALLY.md).

## GitHub deployment

See [docs/PUSH_TO_GITHUB.md](docs/PUSH_TO_GITHUB.md).

## CI/CD

GitHub Actions runs Ruff, mypy, pytest, Bandit, pip-audit, frontend ESLint,
TypeScript/Vite build, and npm audit. Azure deployment is conditional on the
`AZURE_FUNCTIONAPP_NAME` Actions variable and uses OIDC via `azure/login@v2`.

## VS Code pipeline monitoring

Open the repository in VS Code with the recommended GitHub Actions and GitHub
Pull Requests extensions. The Actions view tracks runs after every push or pull
request, shows successful and failed jobs, links commit/PR context, and exposes
step logs and rerun controls. Commit and PR checks remain the source of truth;
workflow summaries include commit SHA, event, ref, repository, and final job
status.

See [docs/GITHUB_PIPELINE_MONITORING.md](docs/GITHUB_PIPELINE_MONITORING.md)
for failure investigation and verification procedures.
