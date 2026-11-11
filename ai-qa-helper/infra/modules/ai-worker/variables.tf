variable "env" {
  description = "Environment name (test | prod). Used as name suffix."
  type        = string
  validation {
    condition     = contains(["test", "prod"], var.env)
    error_message = "env must be test or prod."
  }
}

variable "name_prefix" {
  description = "Prefix for every resource name. qa-ai-deployer is only authorised on this prefix."
  type        = string
  default     = "qa-ai-"
}

variable "execution_role_arn" {
  description = "ARN of the pre-existing Lambda execution role (created by infra). Passed as an ARN instead of a data source because qa-ai-deployer has no iam:GetRole."
  type        = string
}

variable "model_id" {
  description = "Bedrock (Mantle) model ID."
  type        = string
  default     = "anthropic.claude-haiku-5-5"
}

variable "log_retention_days" {
  type    = number
  default = 30
}

# --- Smoke test (S0). Disable after S2. ---
variable "enable_smoke" {
  type    = bool
  default = false
}

variable "smoke_package_path" {
  description = "Path to the Lambda zip built by scripts/build.sh. Required when enable_smoke = true."
  type        = string
  default     = null
}

# --- Worker (S2). Created only when a built package exists. ---
variable "worker_package_path" {
  description = "Path to the Lambda zip built by scripts/build.sh. null = queue only, no worker Lambda yet."
  type        = string
  default     = null
}

variable "worker_timeout_seconds" {
  type    = number
  default = 120
}

variable "worker_memory_mb" {
  type    = number
  default = 1024
}

variable "worker_max_concurrency" {
  description = "SQS event source maximum_concurrency: first brake against Bedrock throttling (min 2)."
  type        = number
  default     = 2
}

variable "worker_batch_size" {
  type    = number
  default = 5
}

variable "max_receive_count" {
  description = "Deliveries before a message moves to the DLQ."
  type        = number
  default     = 3
}
