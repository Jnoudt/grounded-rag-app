# Push the application to GitHub

## Initial repository setup

```powershell
git init
git branch -M main
git add .
git commit -m "Add citation-grounded RAG application"
git remote add origin https://github.com/<owner>/grounded-rag-app.git
git push -u origin main
```

Use a repository remote or SSH key you control. Never commit `.venv`,
`local.settings.json`, `.env`, or Function keys.

## GitHub Actions deployment

Configure these repository secrets for OIDC:

| Secret | Purpose |
|---|---|
| `AZURE_CLIENT_ID` | Deployment app/client ID |
| `AZURE_TENANT_ID` | Microsoft Entra tenant |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription |

Configure this Actions variable:

| Variable | Purpose |
|---|---|
| `AZURE_FUNCTIONAPP_NAME` | Target Azure Functions app name |

Create a federated credential for the GitHub repository and `main` branch or
the deployment environment. The deployment identity needs
`Website Contributor` for the Function app and any required configuration and
role-management permissions. Deployment occurs only on pushes to `main` when
`AZURE_FUNCTIONAPP_NAME` is configured.

## Required branch protections

Enable pull-request review and require the `quality` job in branch protection.
Keep `id-token: write` only on the workflows that need Azure deployment.
