# Log groups are created explicitly so retention is enforced (the Lambda default is "never expire").
resource "aws_cloudwatch_log_group" "smoke" {
  count             = var.enable_smoke ? 1 : 0
  name              = "/aws/lambda/${local.smoke_name}"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "worker" {
  count             = local.create_worker ? 1 : 0
  name              = "/aws/lambda/${local.worker_name}"
  retention_in_days = var.log_retention_days
}
