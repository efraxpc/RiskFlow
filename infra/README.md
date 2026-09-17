# SupportFlow infrastructure

This Terraform root provisions the Azure resources needed by the root SupportFlow application:

- resource group, VNet, and a delegated Container Apps subnet;
- Log Analytics and a Container Apps environment;
- private Azure Container Registry access through managed identity;
- an internal FastAPI Container App and a public Streamlit Container App;
- a separate API identity with `Cognitive Services OpenAI User` on Azure AI;
- optional management of the Azure AI Services account and pinned model deployment.

No API keys are stored in Terraform or Container Apps. The backend authenticates with Microsoft Entra ID and receives inference access through RBAC. The Azure AI endpoint remains public; the API ingress is private to the Container Apps environment.

## Prerequisites

- Terraform 1.9 or newer, Azure CLI, and an Azure subscription.
- `az login` and `az account set --subscription <id>`.
- Permission to create resources and role assignments (Owner, or Contributor plus User Access Administrator).
- Azure OpenAI quota for `gpt-5-mini` in the selected region when creating a new deployment.

Keep Terraform state in a protected remote backend for shared environments. This repository intentionally does not create its own backend because a backend must exist before Terraform initializes this root.

## Deploy

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# Replace subscription_id and review every value.
terraform init
terraform fmt -check
terraform validate
terraform plan -out=bootstrap.tfplan
terraform apply bootstrap.tfplan
```

The first apply leaves the applications disabled so ACR exists before image publication. From `infra/`, build both targets remotely in ACR:

```bash
ACR_NAME="$(terraform output -raw container_registry_name)"
az acr build --registry "$ACR_NAME" --image supportflow-api:dev-001 --target backend --file ../Dockerfile ..
az acr build --registry "$ACR_NAME" --image supportflow-frontend:dev-001 --target frontend --file ../Dockerfile ..
```

Set `deploy_container_apps = true` in `terraform.tfvars`, ensure `image_tag` matches the pushed tag, then deploy:

```bash
terraform plan -out=apps.tfplan
terraform apply apps.tfplan
terraform output -raw frontend_url
```

RBAC can take several minutes to propagate. Retry a request if the first inference returns HTTP 403/503 immediately after deployment.

## Existing versus Terraform-managed Azure AI

The default `manage_ai_resources = false` reads the existing account and avoids conflicting with another Terraform state. To create a new account, set it to `true`, choose a globally unique `ai_account_name`, and set `ai_resource_group_name` to `resource_group_name`.

To adopt the current account instead, first verify it is not managed by another state. Set `manage_ai_resources = true`, run `terraform init`, then import both resources before planning:

```bash
SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
AI_BASE="/subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-rag-manual-generico-dev/providers/Microsoft.CognitiveServices/accounts/rag-manual-foundry-resource"
terraform import 'azurerm_cognitive_account.ai[0]' "$AI_BASE"
terraform import 'azurerm_cognitive_deployment.model[0]' "$AI_BASE/deployments/rag-manual-generico-dev-general"
terraform plan
```

The AI resources have `prevent_destroy`; removal requires an intentional code change. The imported account currently has local keys enabled. Set `ai_local_auth_enabled = false` only after confirming it has no key-based consumers.
