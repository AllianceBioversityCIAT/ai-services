# Base image for AWS Lambda with Python 3.13 runtime
FROM public.ecr.aws/lambda/python:3.13

# Optional: allow passing a custom PYTHONPATH at build time
ARG PYTHONPATH=

# Environment variables:
# - PLAYWRIGHT_BROWSERS_PATH: where Playwright will store browser binaries (must NOT be /tmp for Lambda)
# - PYTHONPATH: include the Lambda task root so imports work correctly
# - PATH: add /var/task/bin in case you install CLIs there
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONPATH="${LAMBDA_TASK_ROOT}:${PYTHONPATH}" \
    PATH="/var/task/bin:${PATH}"

# Copy dependency file first to take advantage of Docker layer caching
COPY requirements.txt .

# Install Python dependencies into the Lambda task root (/var/task)
# This is the standard pattern for Lambda container images
RUN pip install --no-cache-dir -r requirements.txt -t "${LAMBDA_TASK_ROOT}"

# Install Playwright browsers at build time into a PERSISTENT path
# IMPORTANT: Do NOT use /tmp here because /tmp is ephemeral in Lambda at runtime
RUN mkdir -p "${PLAYWRIGHT_BROWSERS_PATH}" && \
    python -m playwright install --with-deps chromium

# Copy the rest of the application code into the Lambda task root
# Make sure main.py contains the "handler" entrypoint defined below
COPY . ${LAMBDA_TASK_ROOT}

# Set the default Lambda handler (file: main.py, function: handler)
CMD ["main.handler"]
