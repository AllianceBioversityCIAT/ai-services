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

variable "bedrock_api" {
  description = "runtime = Bedrock Runtime InvokeModel (bedrock:InvokeModel); mantle = Claude in Amazon Bedrock (bedrock-mantle:CreateInference)."
  type        = string
  default     = "runtime"
  validation {
    condition     = contains(["runtime", "mantle"], var.bedrock_api)
    error_message = "bedrock_api must be runtime or mantle."
  }
}

variable "model_id" {
  description = "Model or inference profile ID. null = us.anthropic.claude-haiku-5-5 (runtime) or anthropic.claude-haiku-5-5 (mantle)."
  type        = string
  default     = null
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
  description = "One job: up to 5 evidence links x 45 s plus the model call (with one retry if truncated)."
  type        = number
  default     = 420
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
  description = "1: each job gets the whole timeout; throughput is set by worker_max_concurrency."
  type        = number
  default     = 1
}

variable "dynamodb_table_name" {
  description = "QA table the worker reads snapshots from and writes suggestions to. null = cgiar-qa-<env>."
  type        = string
  default     = null
}

variable "llm_effort" {
  description = "output_config.effort for Claude (low | medium | high). Set from the v1/v2 comparison."
  type        = string
  default     = "medium"
  validation {
    condition     = contains(["low", "medium", "high"], var.llm_effort)
    error_message = "llm_effort must be low, medium or high."
  }
}

variable "max_receive_count" {
  description = "Deliveries before a message moves to the DLQ."
  type        = number
  default     = 3
}
