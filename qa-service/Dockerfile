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

# Install Playwright system dependencies and browsers
# IMPORTANT:
# - playwright install-deps: instala las librerías del sistema que Chromium necesita
# - playwright install chromium: descarga los binarios de Chromium
# - Se instalan en /opt/pw-browsers (definido en ENV arriba)
RUN mkdir -p "${PLAYWRIGHT_BROWSERS_PATH}" && \
    python -m playwright install-deps chromium && \
    PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH}" python -m playwright install chromium

# Copy the entire application code into the Lambda task root
# Make sure main.py contains the "handler" entrypoint defined below
COPY . ${LAMBDA_TASK_ROOT}

# Set the default Lambda handler (file: main.py, function: handler)
CMD ["main.handler"]