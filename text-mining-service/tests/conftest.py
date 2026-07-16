import os

# Ensure config imports succeed in CI-like environments without a local .env.
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("PRMS_BUCKET_KEY_NAME", "prms/text-mining/files/test")
os.environ.setdefault("STAR_BUCKET_KEY_NAME", "star/text-mining/files/test")
os.environ.setdefault("AICCRA_BUCKET_KEY_NAME", "aiccra/text-mining/files/test")
os.environ.setdefault("CLARISA_VALIDATE_URL", "http://localhost/clarisa/validate")
os.environ.setdefault("MAPPING_URL", "http://localhost/mapping")
os.environ.setdefault("PRMS_FINAL_VALIDATION_ENABLED", "false")