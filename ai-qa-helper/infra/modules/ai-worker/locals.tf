locals {
  queue_name    = "${var.name_prefix}suggestions-${var.env}"
  dlq_name      = "${var.name_prefix}suggestions-dlq-${var.env}"
  worker_name   = "${var.name_prefix}worker-${var.env}"
  smoke_name    = "${var.name_prefix}smoke-${var.env}"
  create_worker = var.worker_package_path != null
}
