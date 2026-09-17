resource "azurerm_container_app" "api" {
  count = var.deploy_container_apps ? 1 : 0

  name                         = "ca-${local.name_prefix}-api"
  container_app_environment_id = azurerm_container_app_environment.app.id
  resource_group_name          = azurerm_resource_group.app.name
  revision_mode                = "Single"
  tags                         = local.common_tags

  identity {
    type = "UserAssigned"
    identity_ids = [
      azurerm_user_assigned_identity.api.id,
      azurerm_user_assigned_identity.registry_pull.id,
    ]
  }

  registry {
    server   = azurerm_container_registry.app.login_server
    identity = azurerm_user_assigned_identity.registry_pull.id
  }

  ingress {
    external_enabled           = false
    allow_insecure_connections = false
    target_port                = 8010
    transport                  = "auto"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 0
    max_replicas = 1

    container {
      name   = "api"
      image  = "${azurerm_container_registry.app.login_server}/supportflow-api:${var.image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      command = ["uvicorn"]
      args = [
        "supportflow.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8010",
        "--workers",
        "1",
        "--no-proxy-headers",
        "--no-access-log",
      ]

      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.api.client_id
      }
      env {
        name  = "SUPPORTFLOW_AZURE_OPENAI_ENABLED"
        value = "true"
      }
      env {
        name  = "SUPPORTFLOW_AZURE_OPENAI_ENDPOINT"
        value = local.ai_endpoint
      }
      env {
        name  = "SUPPORTFLOW_AZURE_OPENAI_DEPLOYMENT"
        value = var.ai_deployment_name
      }
      env {
        name  = "SUPPORTFLOW_AZURE_OPENAI_AUTH"
        value = "entra"
      }
      env {
        name  = "SUPPORTFLOW_AZURE_OPENAI_TIMEOUT_SECONDS"
        value = "30"
      }
      env {
        name  = "SUPPORTFLOW_AZURE_OPENAI_MAX_OUTPUT_TOKENS"
        value = "512"
      }
      env {
        name  = "SUPPORTFLOW_MAX_BODY_BYTES"
        value = "16384"
      }
      env {
        name  = "SUPPORTFLOW_RATE_LIMIT"
        value = "10"
      }
      env {
        name  = "SUPPORTFLOW_RATE_WINDOW_SECONDS"
        value = "60"
      }

      liveness_probe {
        transport        = "HTTP"
        path             = "/health"
        port             = 8010
        interval_seconds = 30
        timeout          = 5
      }

      readiness_probe {
        transport        = "HTTP"
        path             = "/health"
        port             = 8010
        interval_seconds = 10
        timeout          = 5
      }
    }
  }

  depends_on = [
    azurerm_role_assignment.api_openai_user,
    azurerm_role_assignment.registry_pull,
  ]
}

resource "azurerm_container_app" "frontend" {
  count = var.deploy_container_apps ? 1 : 0

  name                         = "ca-${local.name_prefix}-frontend"
  container_app_environment_id = azurerm_container_app_environment.app.id
  resource_group_name          = azurerm_resource_group.app.name
  revision_mode                = "Single"
  tags                         = local.common_tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.registry_pull.id]
  }

  registry {
    server   = azurerm_container_registry.app.login_server
    identity = azurerm_user_assigned_identity.registry_pull.id
  }

  ingress {
    external_enabled           = true
    allow_insecure_connections = false
    target_port                = 8510
    transport                  = "auto"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 0
    max_replicas = 1

    container {
      name   = "frontend"
      image  = "${azurerm_container_registry.app.login_server}/supportflow-frontend:${var.image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      command = ["streamlit"]
      args = [
        "run",
        "streamlit_app.py",
        "--server.address",
        "0.0.0.0",
        "--server.port",
        "8510",
        "--server.headless",
        "true",
      ]

      env {
        name  = "SUPPORTFLOW_API_URL"
        value = "https://${azurerm_container_app.api[0].ingress[0].fqdn}"
      }
      env {
        name  = "SUPPORTFLOW_HTTP_TIMEOUT_SECONDS"
        value = "40"
      }

      liveness_probe {
        transport        = "HTTP"
        path             = "/_stcore/health"
        port             = 8510
        interval_seconds = 30
        timeout          = 5
      }

      readiness_probe {
        transport        = "HTTP"
        path             = "/_stcore/health"
        port             = 8510
        interval_seconds = 10
        timeout          = 5
      }
    }
  }

  depends_on = [azurerm_role_assignment.registry_pull]
}
