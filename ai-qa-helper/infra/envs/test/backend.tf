# State is local for now (gitignored). Migrate to S3 once infra provides a state bucket:
#   1. uncomment the block below and fill the bucket name
#   2. terraform init -migrate-state
# terraform {
#   backend "s3" {
#     bucket       = "<state-bucket-from-infra>"
#     key          = "qa-ai/ai-worker/test.tfstate"
#     region       = "us-east-1"
#     encrypt      = true
#     use_lockfile = true
#   }
# }
