output "queue_url" { value = aws_sqs_queue.suggestions.id }
output "queue_arn" { value = aws_sqs_queue.suggestions.arn }
output "dlq_url" { value = aws_sqs_queue.dlq.id }
output "smoke_function_name" { value = var.enable_smoke ? aws_lambda_function.smoke[0].function_name : null }
output "worker_function_name" { value = local.create_worker ? aws_lambda_function.worker[0].function_name : null }
