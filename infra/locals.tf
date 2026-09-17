locals {
  name_prefix = "supportflow-${var.environment}"
  compact_name = replace(
    "supportflow${var.environment}${random_string.global_suffix.result}",
    "-",
    ""
  )
  container_registry_name = coalesce(var.container_registry_name, substr(local.compact_name, 0, 50))

  common_tags = merge(
    {
      Application = "SupportFlow"
      Environment = var.environment
      ManagedBy   = "Terraform"
    },
    var.tags
  )

  ai_account_id = one(concat(
    azurerm_cognitive_account.ai[*].id,
    data.azurerm_cognitive_account.existing[*].id
  ))
  ai_endpoint = "https://${var.ai_account_name}.services.ai.azure.com/"
}

resource "random_string" "global_suffix" {
  length  = 6
  upper   = false
  special = false
}
