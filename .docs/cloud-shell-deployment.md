# Configure in vscode.dev and deploy to Azure

Use two browser tabs:

- **[Azure Portal](https://portal.azure.com/)** to run a few deployment commands
  in Cloud Shell, starting by cloning the GitHub repository.
- **[VS Code for the Web](https://vscode.dev)** to edit customer configuration
  and save it to GitHub after the initial clone.

vscode.dev is an editor, not a build server: it does not provide a terminal or
run Azure CLI commands. Cloud Shell runs the deployment commands; Azure builds
the Python Function App remotely. No local Python installation is required.

> Deploying and processing documents incur Azure charges. This template uses
> public service endpoints, not private endpoints or VNet integration. Review
> customer policy, permissions, and regional availability before deploying.

## 1. Prepare the customer environment

Confirm these items with the Azure administrator:

| Item | Required value or permission |
| --- | --- |
| Tenant and subscription | The customer tenant ID and target subscription ID. |
| Deployment identity | An interactive user with Contributor plus User Access Administrator at subscription scope, or equivalent approved permissions. Contributor alone cannot create role assignments. |
| Environment name | A short, unique lowercase name such as `contoso-ingest-dev`. |
| Region | An approved region supporting Linux Flex Consumption, AI Search, Document Intelligence, and the embedding deployment below. |
| Azure OpenAI quota | `text-embedding-3-small`, model version `1`, GlobalStandard capacity **30**. GlobalStandard does not guarantee processing stays in the resource's region. |
| Resource providers | `Microsoft.Web`, `Microsoft.Storage`, `Microsoft.EventGrid`, `Microsoft.CognitiveServices`, `Microsoft.Search`, `Microsoft.KeyVault`, `Microsoft.Insights`, `Microsoft.OperationalInsights`. |
| GitHub access | Write access to an approved customer repository containing this solution, and permission to read it from Cloud Shell. |

Use a **private customer-controlled repository** for customer configuration.
If an upstream public repository cannot be forked privately, arrange an
approved private copy rather than assuming a public fork is private. The source
repository is `https://github.com/gregschunemann/doc-ingest-pipeline`.

Never commit passwords, tokens, service keys, or `.env` files. Customer names,
object IDs, and cost-center tags are not credentials, but may still be sensitive
organizational metadata. Keep them out of the public upstream repository.

See the [component and RBAC summary](poc-components-and-rbac.md) for details.

## 2. Open Cloud Shell, select Azure, and clone GitHub

In the customer Azure Portal, select **Cloud Shell** (`>_`) and choose **Bash**.
The terminal label must say **Bash**, not PowerShell.

Choose persistent storage if you want the checkout and deployment `.env` to
survive future sessions. Without storage, session files are lost when the
session ends. Keep files under your home directory.

**Run commands individually. Stop and resolve any error before continuing.**
Do not use `set -euo pipefail` or `exit` in this interactive session; they can
close the shell when a command or check fails.

Replace the example values below with the customer values. Keep `ENV_NAME` and
`LOCATION` consistent with the parameter file in step 4.

```bash
TENANT_ID="replace-with-customer-tenant-id"
SUBSCRIPTION_ID="replace-with-customer-subscription-id"
ENV_NAME="contoso-ingest-dev"
LOCATION="eastus2"
az account set --subscription "$SUBSCRIPTION_ID"
az account show --query '{subscription:id,tenant:tenantId,name:name}' --output json
```

Check the displayed subscription and tenant against your intended values. If
they do not match, switch Portal/Cloud Shell to the customer tenant and stop
until the correct subscription is accessible.

Get the deploying user's **object ID**:

```bash
az ad signed-in-user show --query id --output tsv
```

Copy the result for step 4. This guide assumes a user deployment, not
service-principal automation. An application client ID is not a user object ID.

For a private repository, authenticate to GitHub:

```bash
gh auth login --hostname github.com --web --git-protocol https
gh auth setup-git
```

Follow the browser/device instructions and complete organization SSO approval
if required. Azure sign-in and GitHub sign-in are separate. Never embed a token
in a clone URL.

Clone the customer repository, replacing the example URL:

```bash
git clone https://github.com/CUSTOMER-OWNER/CUSTOMER-REPOSITORY.git "$HOME/doc-ingest-pipeline"
cd "$HOME/doc-ingest-pipeline"
git rev-parse HEAD
```

This creates the Cloud Shell checkout on the repository's default branch.
If the directory already exists, inspect its remote and working tree and use
step 10 instead of cloning over it.

## 3. Open the same GitHub repository in vscode.dev

1. Keep Cloud Shell open and open a second browser tab at
   `https://vscode.dev/github/<customer-owner>/<customer-repository>`.
   Use the **same GitHub owner and repository** you cloned in step 2.
2. Sign in to GitHub when prompted.
3. Use the branch selector in the lower-left corner to select or create the
   approved customer deployment branch, for example `customer-deploy`.
4. Confirm Explorer contains [azure.yaml](../azure.yaml),
   [infra/main.bicep](../infra/main.bicep), and
   [src/functions/requirements.txt](../src/functions/requirements.txt).

**vscode.dev opens GitHub, not the Cloud Shell filesystem.** Cloning first does
not connect the editor directly to that checkout. Edit and commit through
vscode.dev, then synchronize the Cloud Shell checkout in step 5. Configuration
changes are made in the editor, not by generating files with Bash commands.

## 4. Edit the customer Bicep parameter file in vscode.dev

In the vscode.dev Explorer, right-click **infra**, select **New File**, and name
it `customer.bicepparam`. Paste this example, then replace the environment name,
region, principal object ID, and tags with approved customer values:

```bicep
using './main.bicep'

param environmentName = 'contoso-ingest-dev'
param location = 'eastus2'
param principalId = 'replace-with-deploying-user-object-id'
param principalType = 'User'

param searchServiceSku = 'basic'
param openAiSku = 'S0'
param documentIntelligenceSku = 'S0'
param storageSku = 'Standard_LRS'
param useIntegratedVectorization = false

param tags = {
  customer: 'contoso'
  workload: 'document-ingestion'
  costCenter: 'replace-with-approved-cost-center'
}
```

Use ordinary quoted strings and an unquoted Boolean (`true` or `false`).
The `using` path is relative to the parameter file. With the file under `infra`,
`'./main.bicep'` refers to the correct template.

| To customize | Edit |
| --- | --- |
| Resource naming | `environmentName`; the resource group becomes `rg-<environmentName>`. |
| Azure region | `location`; confirm availability and policy first. |
| Deployer data-plane access | `principalId` and `principalType`. |
| AI Search SKU | `searchServiceSku`; `basic` is the starting value, `standard` is another option. Check service capabilities and availability before choosing. |
| Other service SKUs | `openAiSku`, `documentIntelligenceSku`, `storageSku`; use service-supported values. |
| Ingestion mode | `useIntegratedVectorization = false` selects Push mode; `true` selects Integrated Vectorization. |
| Customer metadata | The `tags` object. |

The template's default `azd-env-name`, `azd-template-name`, and
`environment: dev` tags take precedence over matching custom tags.
Production tagging requirements may need a reviewed template change.
Embedding model/capacity, Python version, extraction strategy, network settings,
and index/container/queue names are currently fixed in the template; arbitrary
new `.env` keys cannot override them.

Save the file. Open **Source Control**, review the changes, and use **Commit &
Push** (or **Commit**, then **Sync Changes**, if offered). A suitable message is
`chore(infra): configure customer deployment`. Complete the customer's PR
approval process if required.

**Saving in the editor is not enough:** verify the file appears on the approved
branch in GitHub before continuing. Record that commit SHA.

## 5. Synchronize the Cloud Shell checkout and check tools

Return to the Cloud Shell tab and inspect the existing checkout:

```bash
cd "$HOME/doc-ingest-pipeline"
git status --short
```

If there are local changes, stop and resolve them without discarding work.
With a clean working tree, fetch the branch you used in vscode.dev. Replace
`customer-deploy` if you chose a different branch:

```bash
git fetch origin
git switch customer-deploy
git pull --ff-only
git rev-parse HEAD
```

Compare the displayed commit SHA with the one from step 4. Cloud Shell has a
**separate checkout**; unsaved or unpushed vscode.dev changes are not present
here. Confirm `infra/customer.bicepparam` is present before deploying.

Check the deployment tools:

```bash
az bicep version
azd version
```

If Bicep is missing, run `az bicep install`. If `azd` is missing or outdated, use
the [official installer](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd).
For a home-directory install without administrator access:

```bash
curl -fsSL https://aka.ms/install-azd.sh -o "$HOME/install-azd.sh"
```

Review the downloaded script, then run:

```bash
mkdir -p "$HOME/.local/bin"
bash "$HOME/install-azd.sh" --install-folder "$HOME/.local/share/azd" --symlink-folder "$HOME/.local/bin"
export PATH="$HOME/.local/bin:$PATH"
azd version
```

Use a current stable `azd` supporting Python Flex Consumption remote builds.

## 6. Preview and provision infrastructure

First preview the customer parameter file:

```bash
az deployment sub what-if --name "$ENV_NAME-infra" --location "$LOCATION" --parameters infra/customer.bicepparam
```

Azure CLI compiles the template and parameters. The `using` statement identifies
the template, so no additional `--template-file` argument is needed.
Review the resources, region, SKUs, tags, role assignments, and any replacements
or deletions with the customer. Resolve policy and quota errors before proceeding.

After approval, provision:

```bash
az deployment sub create --name "$ENV_NAME-infra" --location "$LOCATION" --parameters infra/customer.bicepparam --output none
```

Wait for successful completion. In Portal, open the subscription's
**Deployments**, select `<environment>-infra`, and check **Outputs**. Note
`AZURE_RESOURCE_GROUP` and `SERVICE_FUNCTION_NAME`; you will use them next.

## 7. Create the deployment `.env` and deploy code

Sign in to `azd` using the same customer tenant and deploying user:

```bash
azd auth login --tenant-id "$TENANT_ID" --use-device-code
azd env new "$ENV_NAME" --subscription "$SUBSCRIPTION_ID" --location "$LOCATION"
```

This creates `.azure/<environment>/.env` in the Cloud Shell checkout.
It is ignored by Git and is not visible in the separate vscode.dev checkout.

Tell `azd` which provisioned resources to deploy to. Replace the two example
values with the exact Portal deployment outputs from step 6:

```bash
azd env set AZURE_RESOURCE_GROUP "rg-contoso-ingest-dev" --environment "$ENV_NAME"
azd env set SERVICE_FUNCTION_NAME "replace-with-SERVICE_FUNCTION_NAME-output" --environment "$ENV_NAME"
```

Copy the shared utilities into the deployment mirror, then deploy:

```bash
mkdir -p src/functions/utilities
rsync -a --delete --exclude='__pycache__/' --exclude='*.pyc' src/utilities/ src/functions/utilities/
azd deploy function --environment "$ENV_NAME"
```

The `rsync` destination is the ignored generated mirror, not the canonical
`src/utilities` source. Refresh it before every code deployment.

`azd deploy` packages the service, applies [`.funcignore`](../src/functions/.funcignore),
and requests the Python Flex Consumption remote build. Dependencies come from
[requirements.txt](../src/functions/requirements.txt), which specifies
`https://packagefeedproxy.microsoft.io/pypi/simple`. The Azure build environment
must have access to that proxy; resolve feed access or authentication failures
before retrying rather than adding a public-feed fallback.
Check the build/deployment logs for successful dependency installation
and function startup; a ZIP upload alone does not establish success.

**Do not run `azd up` or `azd provision` in this workflow.** They use the existing
`infra/main.parameters.json` mapping, not your customer Bicep parameter file.
Use step 6 for infrastructure and `azd deploy` for code.

### Which configuration file controls what?

| File | How to manage it |
| --- | --- |
| `infra/customer.bicepparam` | Infrastructure source of truth for this workflow. Edit in vscode.dev, commit to the approved private customer repository, and update Cloud Shell before deploying. |
| `.azure/<environment>/.env` | Local `azd` subscription, environment, and deployment-target information. Manage with `azd env set`; do not commit, publish, or copy between customers. Back it up privately if needed. |
| Root `.env` | Optional local application settings. Not needed here and not automatically used by these deployment commands. |
| `src/functions/local.settings.json` | Local Functions host settings. Not required or deployed by this workflow. |

Bicep does not read `.env` automatically. This guide deliberately uses literal
customer values in the Bicep parameter file, avoiding environment-variable
export scripts. Changing `.env` does not change deployed infrastructure or
template-owned Function App settings.

## 8. Verify ingestion in the Azure Portal

1. Open the deployed Function App and its **Functions** view. Allow startup time;
   expect `batch_push_results`, `batch_start_processing`, `add_url_embeddings`,
   and `combine_pages_and_chunknos`. An empty list or worker/import exception
   requires investigation.
2. Open the deployed Storage account, then **Data storage > Containers >
   documents**. Use **Upload** to upload one small approved, non-sensitive PDF
   with a unique filename. Use your Entra user account, not account keys.
3. Wait a few minutes, reopen the blob, and inspect its **Metadata**.
   Under the default Push configuration, expect `embeddings_added` = `true`.
4. Open the deployed AI Search service's **Search explorer**, select
   `doc-ingest-contracts`, and confirm matching chunks for the uploaded file.
   The application creates the index during processing, not provisioning.

Success requires both the completion metadata and matching indexed chunks.
For Integrated Vectorization, also inspect its indexer run status and resulting
index; do not assume the default Push-mode contract destination.

If processing fails, inspect Function App Application Insights exceptions and
**Peek**, rather than dequeue, messages in `doc-processing-poison`.
A 403 may indicate RBAC propagation or the wrong deploying principal.
Do not bypass it with keys or repeatedly upload the document.

## 9. Keep customer configuration private

- Never put credentials or service keys in Bicep parameters or GitHub.
  Service-to-service authentication uses managed identity.
- `.azure/`, root `.env`, and `local.settings.json` are ignored, but ignore rules
  are not encryption or access control.
- The customer Bicep parameter file under `infra` is **not ignored**. Committing
  its noncredential values to the approved private customer repository is
  intentional; do not contribute that file back to the public upstream.
- An ephemeral Cloud Shell session loses its `.env` when closed. Use approved
  persistent storage or recreate the environment and target values in step 7.
- Keep independent environment names and configuration files for different
  customers and stages. Use the corresponding parameter filename explicitly
  in step 6; do not overwrite another customer's values.

## 10. Update or resume

Edit and commit changes in vscode.dev first. In the existing Cloud Shell checkout:

```bash
cd "$HOME/doc-ingest-pipeline"
git status --short
git branch --show-current
```

Only pull if the working tree is clean and the current branch is the approved
deployment branch. If it is dirty or Git reports a conflict, stop rather than
discarding changes.

```bash
git pull --ff-only
git rev-parse HEAD
```

Confirm the new commit matches GitHub.

After reopening Cloud Shell, restore the four variables in step 2, verify the
tenant/subscription again, and restore the user-local `azd` PATH if needed.
Use `azd env select "$ENV_NAME"` instead of `azd env new` when the environment
already exists. Authenticate `azd` again if its session expired.

- **Infrastructure changes:** edit the customer parameter file, synchronize
  Cloud Shell, then repeat step 6. Do not casually change the environment name
  or region of an existing deployment: generated resource names depend on them.
- **Code-only changes:** synchronize Cloud Shell, refresh utilities, and repeat
  the last three commands in step 7. No infrastructure deployment is needed.
- **Rollback:** preserve a known-working package/commit and approved settings
  backup before updates. Flex Consumption has no deployment slots.
- **Cleanup:** resource deletion needs separate customer approval and deletes
  ingested data. Do not delete resources as a troubleshooting shortcut.
  Key Vault purge protection can prevent immediate permanent deletion.

## References

- [VS Code for the Web capabilities and limitations](https://code.visualstudio.com/docs/remote/vscode-web)
- [Cloud Shell and persistence](https://learn.microsoft.com/azure/cloud-shell/features)
- [Bicep parameter files](https://learn.microsoft.com/azure/azure-resource-manager/bicep/parameter-files)
- [Manage `azd` environment files](https://learn.microsoft.com/azure/developer/azure-developer-cli/manage-environment-variables)
- [Azure Functions deployment and remote builds](https://learn.microsoft.com/azure/developer/azure-developer-cli/function-app-deployments)
