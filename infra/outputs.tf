output "resource_group_name" {
  description = "Application resource group."
  value       = azurerm_resource_group.app.name
}

output "container_registry_name" {
  description = "Registry name used by az acr build."
  value       = azurerm_container_registry.app.name
}

output "container_registry_login_server" {
  description = "Registry hostname referenced by Container Apps."
  value       = azurerm_container_registry.app.login_server
}

output "azure_ai_account_id" {
  description = "Managed or referenced Azure AI account ID."
  value       = local.ai_account_id
}

output "azure_ai_endpoint" {
  description = "Azure AI v1 endpoint configured in the API container."
  value       = local.ai_endpoint
}

output "frontend_url" {
  description = "Public Streamlit URL; null until deploy_container_apps is true."
  value = var.deploy_container_apps ? (
    "https://${azurerm_container_app.frontend[0].ingress[0].fqdn}"
  ) : null
}

output "backend_internal_url" {
  description = "Environment-internal FastAPI URL; null until deploy_container_apps is true."
  value = var.deploy_container_apps ? (
    "https://${azurerm_container_app.api[0].ingress[0].fqdn}"
  ) : null
}
