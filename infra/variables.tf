variable "subscription_id" {
  description = "Azure subscription where SupportFlow resources are deployed."
  type        = string
  nullable    = true
  default     = null
}

variable "location" {
  description = "Azure region for the application infrastructure."
  type        = string
  default     = "brazilsouth"
}

variable "environment" {
  description = "Short environment name used in resource names and tags."
  type        = string
  default     = "dev"

  validation {
    condition     = can(regex("^[a-z0-9-]{2,10}$", var.environment))
    error_message = "environment must contain 2-10 lowercase letters, numbers, or hyphens."
  }
}

variable "resource_group_name" {
  description = "Resource group for the SupportFlow application infrastructure."
  type        = string
  default     = "rg-supportflow-dev"
}

variable "container_registry_name" {
  description = "Globally unique ACR name. Null generates supportflow<environment><random>."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition = var.container_registry_name == null || can(regex(
      "^[a-zA-Z0-9]{5,50}$",
      var.container_registry_name
    ))
    error_message = "container_registry_name must be 5-50 alphanumeric characters."
  }
}

variable "deploy_container_apps" {
  description = "Create Container Apps after both application images have been pushed to ACR."
  type        = bool
  default     = false
}

variable "image_tag" {
  description = "Immutable tag shared by the backend and frontend images."
  type        = string
  default     = "dev"

  validation {
    condition     = can(regex("^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$", var.image_tag))
    error_message = "image_tag must be a valid non-empty container image tag."
  }
}

variable "vnet_address_space" {
  description = "Address space for the Container Apps virtual network."
  type        = list(string)
  default     = ["10.42.0.0/16"]
}

variable "container_apps_subnet_cidr" {
  description = "Dedicated /21-or-larger subnet delegated to Container Apps."
  type        = string
  default     = "10.42.0.0/21"
}

variable "log_retention_days" {
  description = "Log Analytics retention period."
  type        = number
  default     = 30

  validation {
    condition     = var.log_retention_days >= 30 && var.log_retention_days <= 730
    error_message = "log_retention_days must be between 30 and 730."
  }
}

variable "manage_ai_resources" {
  description = "Create/manage the Azure AI account and deployment instead of reading an existing account."
  type        = bool
  default     = false
}

variable "ai_resource_group_name" {
  description = "Resource group containing Azure AI. It must already exist unless it equals resource_group_name."
  type        = string
  default     = "rg-rag-manual-generico-dev"
}

variable "ai_account_name" {
  description = "Globally unique Azure AI Services account name."
  type        = string
  default     = "rag-manual-foundry-resource"
}

variable "ai_location" {
  description = "Region of the Azure AI account and model deployment."
  type        = string
  default     = "brazilsouth"
}

variable "ai_deployment_name" {
  description = "Azure AI model deployment name used by SupportFlow."
  type        = string
  default     = "rag-manual-generico-dev-general"
}

variable "ai_model_name" {
  description = "Model catalog name used when manage_ai_resources is true."
  type        = string
  default     = "gpt-5-mini"
}

variable "ai_model_version" {
  description = "Pinned model version used when manage_ai_resources is true."
  type        = string
  default     = "2025-08-07"
}

variable "ai_deployment_sku" {
  description = "Azure AI deployment SKU."
  type        = string
  default     = "GlobalStandard"
}

variable "ai_deployment_capacity" {
  description = "Deployment capacity in thousands of tokens per minute."
  type        = number
  default     = 10

  validation {
    condition     = var.ai_deployment_capacity > 0
    error_message = "ai_deployment_capacity must be greater than zero."
  }
}

variable "ai_local_auth_enabled" {
  description = "Keep account keys enabled. Disable only after confirming every consumer uses Entra ID."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Additional tags merged into every supported resource."
  type        = map(string)
  default     = {}
}
