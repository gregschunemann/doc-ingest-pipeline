# doc-ingest-pipeline: POC Component Summary and Azure RBAC

> Audience: customer POC planning. Scope: what gets deployed, how each piece is used, and which Azure roles are needed to deploy, operate, and consume it.
> Deployment mechanics are intentionally out of scope. See the [README](../README.md) for the deployment flow.
> Source of truth: [infra/main.bicep](../infra/main.bicep) and [role-assignments.bicep](../infra/modules/roleassignments/role-assignments.bicep).

## 1. Solution in one paragraph

A headless, event-driven ingestion service. A document uploaded to Blob Storage raises an Event Grid event, which lands in a Storage Queue. A queue-triggered Azure Function parses the document with Document Intelligence, chunks it, embeds the chunks with Azure OpenAI, and writes chunks and vectors to Azure AI Search. There is no UI. Downstream RAG, search, or agent solutions query the Search indexes directly.

```text
Uploader -> Blob (documents) -> Event Grid system topic -> Queue (doc-processing)
         -> Function App (managed identity) -> Document Intelligence -> Azure OpenAI (embeddings) -> AI Search
                                            \-> poison queue on repeated failure
```

## 2. Components and usage

All resources are created in one resource group (`rg-<environmentName>`) in a single region. Names use an `<abbreviation><resourceToken>` pattern.

| # | Component | Configuration in this template | How it is used |
| - | --------- | ------------------------------ | -------------- |
| 1 | **Resource Group** | Subscription-scoped deployment creates `rg-<env>`. | Container and RBAC boundary for everything below. |
| 2 | **Storage Account** | Standard_LRS, TLS 1.2, public blob access off, shared-key access currently **enabled**. | Holds the `documents` container (uploads), the `app-package` container (Function deployment package), the `doc-processing` and `doc-processing-poison` queues, and the Function runtime state (`AzureWebJobsStorage`, identity-based). |
| 3 | **Event Grid system topic and subscription** | Source is the storage account. Delivers `BlobCreated` only to the `doc-processing` queue. Up to 30 delivery attempts. | Turns an upload into a queue message. Deletions are not propagated automatically. |
| 4 | **Function App and App Service Plan** | Linux Flex Consumption (FC1), Python 3.11, 2 GB instances, max 100 instances, system-assigned managed identity, HTTPS only, FTPS off. | Runs the ingestion code. Details in section 3. |
| 5 | **Azure AI Document Intelligence** | `FormRecognizer`, S0, custom subdomain, public network, local (key) auth enabled. | Parses documents with `prebuilt-layout` (general), `prebuilt-read` (text only), or `prebuilt-contract` (contract entities). Default strategy in the template is `contract`. |
| 6 | **Azure OpenAI** and `text-embedding-3-small` deployment | S0, model version 1, GlobalStandard capacity 30, 1536 dimensions, public network, key auth enabled. | Generates embeddings for each chunk in push mode. Quota and regional availability must be confirmed up front. |
| 7 | **Azure AI Search** | Basic SKU, 1 replica, 1 partition, public network, API-key and Entra auth both allowed. | Stores chunks and vectors. The app creates `doc-ingest-index` (general) and `doc-ingest-contracts` (contracts) on first processing. Query these from downstream apps. |
| 8 | **Key Vault** | Standard, RBAC authorization, soft delete 90 days, **purge protection on**, public network. | Optional secret store for key-based fallback. The default managed-identity path does not read secrets. Treat it as provisioned but largely idle in the POC. |
| 9 | **Log Analytics and Application Insights** | PerGB2018, 30-day retention. | Function telemetry, traces, failures, and the main troubleshooting surface. |
| 10 | **Role assignments** | 9 data-plane grants to the Function identity and 2 to the deployer. See section 4. | Gives the managed identity least-privilege access, so no keys are needed. |

## 3. Function App endpoints

| Function | Trigger | Auth | Purpose |
| -------- | ------- | ---- | ------- |
| `batch_push_results` | Queue `doc-processing` | n/a (identity) | Core pipeline: parse, chunk, embed, index. On success stamps blob metadata `embeddings_added=true`. Handles `BlobCreated`, and `BlobDeleted` if that event is ever routed. |
| `batch_start_processing` | HTTP POST `/api/BatchStartProcessing` | Function key | Re-enqueues **every** blob in the container, so it is a full re-index and incurs cost. In integrated-vectorization mode it runs the Search indexer instead. |
| `add_url_embeddings` | HTTP POST `/api/AddURLEmbeddings` | Function key | Ingests a web URL. Push mode embeds inline. Integrated-vectorization mode uploads the text to Blob. |
| `combine_pages_and_chunknos` | HTTP | **Anonymous** | Helper for the Search WebApiSkill, used only in integrated-vectorization mode. |

Two embedding modes exist, selected by `AZURE_SEARCH_USE_INTEGRATED_VECTORIZATION`. **Push** (default) embeds in the Function. **Integrated Vectorization** uses the Search indexer and skillset. Use push mode for the POC.

## 4. What the POC produces

- A searchable vector index of the uploaded documents, with contract-specific fields when the `contract` strategy is used.
- Blob metadata `embeddings_added=true` as the idempotency marker per document.
- Telemetry in Application Insights, and failed items in `doc-processing-poison`.

## 5. Azure roles

### 5.1 Identities involved

| Identity | Description |
| -------- | ----------- |
| **Deployer** | The person or pipeline that provisions the solution. |
| **Function App managed identity** | System-assigned. Created at deploy time and granted data-plane roles by the template. |
| **Operator** | Day-2 support: monitoring, queue triage, re-processing. |
| **Content contributor** | People or systems that upload documents. |
| **Consumer** | Downstream apps or users that query the Search indexes. |

### 5.2 Deployer: roles to create the solution

The template is **subscription-scoped**, because it creates the resource group. It also creates role assignments. So the deployer needs both of the following at subscription scope:

| Need | Built-in role (any one combination) |
| ---- | ----------------------------------- |
| Create the RG and all resources, register providers | **Contributor** (or Owner) |
| Create the role assignments in the template (`Microsoft.Authorization/roleAssignments/write`) | **User Access Administrator**, or **Role Based Access Control Administrator**, or **Owner** |

Notes:

- **Contributor alone fails** at the role-assignment step.
- Owner at subscription scope satisfies both needs. The least-privilege option is Contributor plus Role Based Access Control Administrator. The RBAC Administrator role can be constrained with a condition to the specific roles listed in 5.3.
- If the customer pre-creates the resource group, the same roles are needed at RG scope. The template would then need adjusting, which is a topic for the working session.
- Resource providers must be registered: `Microsoft.Web`, `Microsoft.Storage`, `Microsoft.EventGrid`, `Microsoft.CognitiveServices`, `Microsoft.Search`, `Microsoft.KeyVault`, `Microsoft.Insights`, `Microsoft.OperationalInsights`. Registration needs Contributor or higher, or a subscription admin to do it ahead of time.
- Code deployment to the Function App uploads a package to the `app-package` blob container using the deployer's identity. This works because the template grants the deployer **Storage Blob Data Contributor** (see 5.3). Contributor is a management-plane role and does not allow blob data access.
- **Entra ID directory roles are not required.** The deployer only needs to resolve their own object ID. No app registrations or directory roles are used.
- **Azure OpenAI quota** (GlobalStandard, 30 units of `text-embedding-3-small`) must be available in the subscription and region. This is a capacity check, not a role. Without it the deployment fails.
- Subscription policy (allowed regions, required tags, denied public network access, shared-key denial) can block the deployment regardless of role.

### 5.3 Roles the template grants automatically

These are created by [role-assignments.bicep](../infra/modules/roleassignments/role-assignments.bicep). No manual action is needed.

**Function App managed identity (service-to-service)**

| Scope | Role | Role ID | Why |
| ----- | ---- | ------- | --- |
| Storage account | Storage Blob Data Contributor | `ba92f5b4-2d11-453d-a403-e96b0029c9fe` | Read source documents, write the `embeddings_added` metadata, and write to Blob in URL-ingest mode. |
| Storage account | Storage Queue Data Contributor | `974c5e8b-45b9-4653-ba55-5f855dd0fb88` | Trigger on, read, and enqueue `doc-processing` messages. Used by `BatchStartProcessing`. |
| Storage account | Storage Blob Delegator | `db58b8e5-c6ad-4a2a-8342-4190687cbf4a` | Get a user-delegation key to issue SAS URLs for Document Intelligence to read blobs. |
| Storage account | Storage Table Data Contributor | `0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3` | Flex Consumption host state (identity-based `AzureWebJobsStorage`). |
| AI Search | Search Index Data Contributor | `8ebe5a00-799e-43f5-93ac-243d3dce84a7` | Write and delete documents in the indexes. |
| AI Search | Search Service Contributor | `7ca78c08-252a-4471-8644-bb5ff32d4ba0` | Create and update indexes, indexers, and skillsets. |
| Document Intelligence | Cognitive Services User | `a97b65f3-24c7-4388-baec-2e87135dc908` | Call the analyze APIs. |
| Azure OpenAI | Cognitive Services OpenAI User | `5e0bd9bd-7b93-4f28-af87-19fc36ad61bd` | Call the embeddings API. |
| Key Vault | Key Vault Secrets User | `4633458b-17de-408a-b874-0445c86b69e6` | Read secrets (key-fallback only). |

**Event Grid** needs no assignment. The system-topic-to-queue delivery works without a managed-identity role.

**Deployer (RG scope)**

| Role | Role ID | Why |
| ---- | ------- | --- |
| Storage Blob Data Contributor | `ba92f5b4-2d11-453d-a403-e96b0029c9fe` | Upload the Function package and test documents, using Entra auth. |
| Search Index Data Reader | `1407120a-92aa-4202-b7e9-c0e197c71c8f` | Inspect indexes in Search explorer. |

These two are assigned to whichever principal ID is passed at deploy time. Remove or replace them with group-based assignments after the POC if the customer requires it.

### 5.4 Operate and use: recommended roles

These are not created by the template (except the deployer pair above). Assign them as needed, preferably to Entra groups.

| Persona | Task | Recommended role and scope |
| ------- | ---- | -------------------------- |
| **Content contributor** | Upload documents | **Storage Blob Data Contributor** on the `documents` container. Use Storage Blob Data Reader for read-only visibility. |
| **Operator** | Peek poison queue and check pipeline | **Storage Queue Data Reader** (peek) or **Storage Queue Data Contributor** (requeue or clear) on the storage account. |
| **Operator** | View telemetry and failures | **Monitoring Reader** on the RG, plus **Log Analytics Reader** on the workspace, or **Reader** at RG scope as a minimum. |
| **Operator** | Change app settings, restart, get Function keys | **Website Contributor** on the Function App. Reading keys is a management-plane action, so it needs this or Contributor. |
| **Operator** | Manage Search indexes, or run an indexer | **Search Service Contributor** on the Search service. |
| **Operator** | Inspect or change index data | **Search Index Data Reader** or **Search Index Data Contributor** on the Search service. |
| **Consumer (downstream app or user)** | Query the indexes | **Search Index Data Reader** on the Search service (or on specific indexes). Use a managed identity for apps. |
| **Consumer** | Call `BatchStartProcessing` or `AddURLEmbeddings` | No Azure role. They need the **Function key** in the `x-functions-key` header. |
| **Platform admin** | Full lifecycle, cost, and policy | **Contributor** on the RG, and **User Access Administrator** or **RBAC Administrator** if they manage assignments. |
| **Security or audit** | Review configuration | **Reader** at RG scope, and **Security Reader** if Defender for Cloud is used. |

RBAC propagation can take several minutes after assignment. Plan for this during the working session.

## 6. Items to settle with the customer before the working session

1. **Region and quota.** Confirm that the `text-embedding-3-small` GlobalStandard capacity is available. GlobalStandard does not keep processing in the resource's region. If data residency matters, the template must change.
2. **Network posture.** Everything is public today. No private endpoints or VNET integration are included. Confirm whether the customer policy allows that for a POC.
3. **Shared-key and local auth.** The template leaves storage shared-key access and key auth on Search, Document Intelligence, and OpenAI **enabled** as a fallback. Comments in the Function module say shared key is disabled, but `main.bicep` sets it to `true`. The identity-based settings mean it can probably be turned off. Validate this against customer policy, because many tenants deny shared-key access.
4. **Principal for deployer grants.** Decide whether the Storage Blob Data Contributor and Search Index Data Reader grants go to a named user, a group, or a service principal.
5. **Function keys and the anonymous helper.** HTTP endpoints rely on Function keys. Decide who holds them. The `combine_pages_and_chunknos` helper is anonymous. If integrated-vectorization mode is not used, consider disabling it.
6. **Cost guardrails.** Max instances is 100. For a POC, cap this low to protect Document Intelligence and OpenAI throughput and spend. `BatchStartProcessing` reprocesses everything, so restrict who gets the key.
7. **Integrated vectorization mode.** If chosen, the Search service's own managed identity needs additional roles that the template does not grant today. It needs Storage Blob Data Reader on Storage and Cognitive Services OpenAI User on OpenAI. Stay in push mode for the POC to avoid this.
8. **Key Vault purge protection.** It is on, so a deleted vault name stays reserved for the retention period. This matters if the POC is torn down and recreated with the same name.
9. **Role assignment count output.** The `functionAppRoleAssignmentsCount` output in the role-assignments module says 8, but 9 Function identity assignments are actually created. This is cosmetic.
10. **Deletion handling.** Only `BlobCreated` events are routed. Deleting a source blob does not remove its chunks from the index.

## 7. Quick reference: minimum role set for the POC

| Who | Roles |
| --- | ----- |
| Deployer | Contributor + User Access Administrator (or Role Based Access Control Administrator), at subscription scope |
| Function managed identity | The 9 assignments in 5.3 (automatic) |
| Uploader | Storage Blob Data Contributor on `documents` |
| Operator | Website Contributor on the Function App, Storage Queue Data Reader on Storage, Monitoring Reader or Reader on the RG, Search Index Data Reader on Search |
| Downstream consumer | Search Index Data Reader on Search |
