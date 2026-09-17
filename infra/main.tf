resource "azurerm_resource_group" "app" {
  name     = var.resource_group_name
  location = var.location
  tags     = local.common_tags
}

resource "azurerm_virtual_network" "app" {
  name                = "vnet-${local.name_prefix}"
  location            = azurerm_resource_group.app.location
  resource_group_name = azurerm_resource_group.app.name
  address_space       = var.vnet_address_space
  tags                = local.common_tags
}

resource "azurerm_subnet" "container_apps" {
  name                 = "snet-container-apps"
  resource_group_name  = azurerm_resource_group.app.name
  virtual_network_name = azurerm_virtual_network.app.name
  address_prefixes     = [var.container_apps_subnet_cidr]

  delegation {
    name = "container-apps"

    service_delegation {
      name    = "Microsoft.App/environments"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_log_analytics_workspace" "app" {
  name                = "log-${local.name_prefix}"
  location            = azurerm_resource_group.app.location
  resource_group_name = azurerm_resource_group.app.name
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days
  tags                = local.common_tags
}

resource "azurerm_container_app_environment" "app" {
  name                       = "cae-${local.name_prefix}"
  location                   = azurerm_resource_group.app.location
  resource_group_name        = azurerm_resource_group.app.name
  infrastructure_subnet_id   = azurerm_subnet.container_apps.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.app.id
  logs_destination           = "log-analytics"
  public_network_access      = "Enabled"
  tags                       = local.common_tags
}

resource "azurerm_container_registry" "app" {
  name                          = local.container_registry_name
  location                      = azurerm_resource_group.app.location
  resource_group_name           = azurerm_resource_group.app.name
  sku                           = "Basic"
  admin_enabled                 = false
  anonymous_pull_enabled        = false
  public_network_access_enabled = true
  tags                          = local.common_tags
}

resource "azurerm_user_assigned_identity" "registry_pull" {
  name                = "id-${local.name_prefix}-acr-pull"
  location            = azurerm_resource_group.app.location
  resource_group_name = azurerm_resource_group.app.name
  tags                = local.common_tags
}

resource "azurerm_user_assigned_identity" "api" {
  name                = "id-${local.name_prefix}-api"
  location            = azurerm_resource_group.app.location
  resource_group_name = azurerm_resource_group.app.name
  tags                = local.common_tags
}

resource "azurerm_role_assignment" "registry_pull" {
  scope                            = azurerm_container_registry.app.id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_user_assigned_identity.registry_pull.principal_id
  skip_service_principal_aad_check = true
}
