# Base image for AWS Lambda with Python 3.13 runtime
FROM public.ecr.aws/lambda/python:3.13

# Optional: allow passing a custom PYTHONPATH at build time
ARG PYTHONPATH=

# Environment variables:
# - PLAYWRIGHT_BROWSERS_PATH: where Playwright will store browser binaries
#   IMPORTANT: Must NOT be /tmp because /tmp is ephemeral at runtime
# - PYTHONPATH: include the Lambda task root so imports work correctly
# - PATH: add /var/task/bin in case you install CLIs there
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
    PYTHONPATH="${LAMBDA_TASK_ROOT}:${PYTHONPATH}" \
    PATH="/var/task/bin:${PATH}"

# Copy dependency file first to take advantage of Docker layer caching
COPY requirements.txt .

# Install Python dependencies into the Lambda task root (/var/task)
# This is the standard pattern for Lambda container images
RUN pip install --no-cache-dir -r requirements.txt -t "${LAMBDA_TASK_ROOT}"

# Install Playwright Chromium browsers only (no system deps)
# IMPORTANT:
# - The Lambda base image already has system dependencies for Chromium
# - We only need to download the Chromium binary
# - Use --with-deps=false to skip attempting system package installation
RUN mkdir -p "${PLAYWRIGHT_BROWSERS_PATH}" && \
    PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH}" python -m playwright install --with-deps=false chromium

# Copy the entire application code into the Lambda task root
# Make sure main.py contains the "handler" entrypoint defined below
COPY . ${LAMBDA_TASK_ROOT}

# Set the default Lambda handler (file: main.py, function: handler)
CMD ["main.handler"]