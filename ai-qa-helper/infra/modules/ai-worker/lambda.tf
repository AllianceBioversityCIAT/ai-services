# Both functions ship the same zip built by scripts/build.sh (Python 3.13, arm64 wheels).

# ---------- Smoke test (S0) ----------
resource "aws_lambda_function" "smoke" {
  count            = var.enable_smoke ? 1 : 0
  function_name    = local.smoke_name
  description      = "P2-3918 S0: one Haiku 5.5 call via Bedrock. Remove after S2."
  role             = var.execution_role_arn
  runtime          = "python3.13"
  architectures    = ["arm64"]
  handler          = "app.handlers.smoke.handler"
  filename         = var.smoke_package_path
  source_code_hash = filebase64sha256(var.smoke_package_path)
  timeout          = 30
  memory_size      = 256

  environment {
    variables = { MODEL_ID = local.model_id, BEDROCK_API = var.bedrock_api }
  }

  depends_on = [aws_cloudwatch_log_group.smoke]
}

# ---------- Worker (S2) ----------
resource "aws_lambda_function" "worker" {
  count            = local.create_worker ? 1 : 0
  function_name    = local.worker_name
  description      = "P2-3918 AI suggestion worker (SQS -> Bedrock -> DynamoDB)."
  role             = var.execution_role_arn
  runtime          = "python3.13"
  architectures    = ["arm64"]
  handler          = "app.handlers.worker.handler"
  filename         = var.worker_package_path
  source_code_hash = filebase64sha256(var.worker_package_path)
  timeout          = var.worker_timeout_seconds
  memory_size      = var.worker_memory_mb

  environment {
    variables = {
      MODEL_ID          = local.model_id
      BEDROCK_API       = var.bedrock_api
      ENV_NAME          = var.env
      TABLE_NAME        = coalesce(var.dynamodb_table_name, "cgiar-qa-${var.env}")
      LLM_EFFORT        = var.llm_effort
      MAX_RECEIVE_COUNT = tostring(var.max_receive_count)
    }
  }

  depends_on = [aws_cloudwatch_log_group.worker]
}

resource "aws_lambda_event_source_mapping" "worker" {
  count                   = local.create_worker ? 1 : 0
  event_source_arn        = aws_sqs_queue.suggestions.arn
  function_name           = aws_lambda_function.worker[0].arn
  batch_size              = var.worker_batch_size
  function_response_types = ["ReportBatchItemFailures"]

  scaling_config {
    maximum_concurrency = var.worker_max_concurrency
  }
}
