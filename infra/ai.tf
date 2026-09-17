data "azurerm_cognitive_account" "existing" {
  count = var.manage_ai_resources ? 0 : 1

  name                = var.ai_account_name
  resource_group_name = var.ai_resource_group_name
}

resource "azurerm_cognitive_account" "ai" {
  count = var.manage_ai_resources ? 1 : 0

  name                          = var.ai_account_name
  location                      = var.ai_location
  resource_group_name           = var.ai_resource_group_name
  kind                          = "AIServices"
  sku_name                      = "S0"
  custom_subdomain_name         = var.ai_account_name
  local_auth_enabled            = var.ai_local_auth_enabled
  project_management_enabled    = true
  public_network_access_enabled = true
  tags                          = local.common_tags

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [azurerm_resource_group.app]
}

resource "azurerm_cognitive_deployment" "model" {
  count = var.manage_ai_resources ? 1 : 0

  name                   = var.ai_deployment_name
  cognitive_account_id   = azurerm_cognitive_account.ai[0].id
  rai_policy_name        = "Microsoft.DefaultV2"
  version_upgrade_option = "NoAutoUpgrade"

  model {
    format  = "OpenAI"
    name    = var.ai_model_name
    version = var.ai_model_version
  }

  sku {
    name     = var.ai_deployment_sku
    capacity = var.ai_deployment_capacity
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_role_assignment" "api_openai_user" {
  scope                            = local.ai_account_id
  role_definition_name             = "Cognitive Services OpenAI User"
  principal_id                     = azurerm_user_assigned_identity.api.principal_id
  skip_service_principal_aad_check = true
}
