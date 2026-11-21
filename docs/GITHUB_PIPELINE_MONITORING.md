# GitHub pipeline monitoring from VS Code

## Workspace setup

1. Open this repository in VS Code.
2. Install the recommended workspace extensions when prompted.
3. Sign in to the GitHub extension.
4. Open **GitHub Actions** in the VS Code Activity Bar.
5. Select this repository and the `App quality, test, and deployment` workflow.

The workspace recommends:

- GitHub Actions for workflow runs, job logs, reruns, and commit status.
- GitHub Pull Requests for PR checks, review comments, and issue tracking.
- Python, Pylance, Ruff, mypy, ESLint, and Prettier for local verification.

## Push and commit tracking

Every push to `main` and every pull request triggers the `quality` job.
The workflow publishes:

- Commit SHA and GitHub event context.
- A job summary that includes the final quality status.
- Frontend build artifacts for completed builds.
- Successful or failed commit checks attached to the commit and PR.
- Azure deployment only for pushes to `main` when
  `AZURE_FUNCTIONAPP_NAME` is configured.

Local commits do not trigger GitHub Actions until they are pushed. VS Code
notifications and the GitHub Actions view update automatically as runs complete.
Branch protection should require the `quality` check before merge.

## Investigating a failure

1. Open the failed run in the GitHub Actions VS Code view.
2. Expand the failing job and identify the exact step.
3. Open step logs and copy the first actionable error.
4. Reproduce locally:

   ```powershell
   python -m pytest
   ruff check src function_app.py tests
   mypy src function_app.py
   bandit -q -r src function_app.py
   pip-audit -r requirements.txt
   cd frontend
   npm run lint
   npm run build
   npm run audit
   ```

5. Fix the root cause and run the smallest relevant test.
6. Commit and push the fix with a description of the failure, correction, and
   verification performed.
7. Confirm the new commit check is green in VS Code before merging or deploying.

## Successful development verification

Before confirming a development change:

- Tests pass locally and in the `quality` job.
- Ruff, mypy, Bandit, and dependency audits report no blocking findings.
- Frontend lint, build, and audit complete successfully.
- The commit has a green GitHub check.
- The job summary and frontend artifact correspond to the expected commit SHA.

## Resolving a development issue

Use PR comments or VS Code Problems for local diagnostics. Add a regression test
before or alongside the fix. For Azure deployment failures, verify OIDC
secrets/variables, the federated credential subject, branch/environment
configuration, and target Function app name. Do not add secrets to repository
files or VS Code settings.
