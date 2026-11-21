# Security and Governance

## Identity and secrets

- Use `DefaultAzureCredential` for Azure Blob Storage, Cosmos DB, Azure AI
  Search, Azure AI Services, and Application Insights.
- Do not use account keys or connection strings for data-plane access. Key Vault
  may hold only operational configuration that is not available through RBAC.
- Never commit secrets, local credentials, or deployment output connection
  strings.
- Keep a deterministic mock mode for offline tests and development.

## Phase 1 infrastructure contract

The application configuration must use these Terraform outputs and names:

| Purpose | Terraform output or resource | Application environment variable |
|---|---|---|
| Storage account | `storage_account_name` | `AZURE_STORAGE_ACCOUNT_NAME` |
| Blob endpoint | `storage_blob_endpoint` | `AZURE_STORAGE_BLOB_ENDPOINT` |
| Documents container | `documents` | `AZURE_STORAGE_DOCUMENTS_CONTAINER` |
| Evaluations container | `evaluations` | `AZURE_STORAGE_EVALUATIONS_CONTAINER` |
| Cosmos endpoint | `cosmos_endpoint` | `AZURE_COSMOS_ENDPOINT` |
| Cosmos database | `cosmos_database_name` | `AZURE_COSMOS_DATABASE_NAME` |
| Cosmos evaluation container | `cosmos_container_name` | `AZURE_COSMOS_CONTAINER_NAME` |
| Azure AI Search | `search_endpoint` | `AZURE_SEARCH_ENDPOINT` |
| Azure AI Services | `ai_endpoint` | `AZURE_AI_ENDPOINT` |
| Managed identity | `managed_identity_client_id` | `AZURE_CLIENT_ID` |
| Telemetry | `application_insights_connection_string` | `APPLICATIONINSIGHTS_CONNECTION_STRING` |

The environment variable names are application-facing names. The Terraform
resource names remain `documents`, `evaluations`, `grounded-rag`, and
`evaluation-results` for the storage containers and Cosmos database/container
respectively.

## Retrieval boundary

Retrieved document text is untrusted input. Citations are verified against the
retrieved chunk set before they are included in a response. Context sent to a
model must be delimitated, and instructions in retrieved text must never be
treated as system or developer instructions.

## Provenance and abstention

Every chunk receives a deterministic `{doc_slug}_p{page}_c{idx}` ID. Answers
must cite only retrieved chunk IDs and may abstain when evidence is missing,
weak, or contradictory. The verifier rejects claims with unknown citations,
insufficient lexical support, or relevance below the configured threshold.

## Logging and data handling

- Emit structured JSON logs with correlation and trace IDs.
- Redact secrets, authorization headers, connection strings, and stack traces
  containing sensitive source values.
- Avoid logging full document text or retrieved context.
- Do not expose infrastructure or SDK exception details to API clients.
