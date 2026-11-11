resource "aws_sqs_queue" "dlq" {
  name                      = local.dlq_name
  message_retention_seconds = 1209600 # 14 days, time to inspect and redrive
  sqs_managed_sse_enabled   = true
}

resource "aws_sqs_queue" "suggestions" {
  name                       = local.queue_name
  visibility_timeout_seconds = var.worker_timeout_seconds * 6 # AWS guidance for Lambda consumers
  message_retention_seconds  = 345600                         # 4 days
  receive_wait_time_seconds  = 20
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = var.max_receive_count
  })
}

resource "aws_sqs_queue_redrive_allow_policy" "dlq" {
  queue_url = aws_sqs_queue.dlq.id
  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.suggestions.arn]
  })
}
