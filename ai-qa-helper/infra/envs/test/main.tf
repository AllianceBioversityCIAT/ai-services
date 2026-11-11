provider "aws" {
  region = "us-east-1"
  default_tags {
    tags = {
      Project     = "qa-ai" # infra tracking tag (key is case-sensitive)
      environment = "test"
      managed_by  = "terraform"
      ticket      = "P2-3918"
    }
  }
}

variable "execution_role_arn" {
  description = "ARN of the Lambda execution role created by infra."
  type        = string
}

variable "enable_smoke" {
  type    = bool
  default = false
}

variable "enable_worker" {
  type    = bool
  default = false
}

variable "lambda_package_path" {
  description = "Zip built by scripts/build.sh (one package for the smoke test and the worker)."
  type        = string
  default     = "../../../dist/ai-qa-helper-lambda.zip"
}

module "ai_worker" {
  source              = "../../modules/ai-worker"
  env                 = "test"
  execution_role_arn  = var.execution_role_arn
  enable_smoke        = var.enable_smoke
  smoke_package_path  = var.lambda_package_path
  worker_package_path = var.enable_worker ? var.lambda_package_path : null
}

output "queue_url" { value = module.ai_worker.queue_url }
output "dlq_url" { value = module.ai_worker.dlq_url }
output "smoke_function_name" { value = module.ai_worker.smoke_function_name }
output "worker_function_name" { value = module.ai_worker.worker_function_name }
