# Change base image to Debian for better package support
FROM debian:bullseye-slim

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

# Install system dependencies
RUN apt-get update && apt-get install -y \
    apt-utils \
    software-properties-common \
    libnspr4 \
    libnss3 \
    libnssutil3 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libexpat1 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxcb1 \
    libxkbcommon0 \
    libudev1 \
    libasound2 \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Install Python and pip
RUN apt-get install -y python3 python3-pip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --no-cache-dir --upgrade pip

# Copy dependency file first to take advantage of Docker layer caching
COPY requirements.txt .

# Install Python dependencies into the Lambda task root (/var/task)
RUN pip install --no-cache-dir -r requirements.txt -t /var/task

# Install Playwright Chromium browsers only
RUN mkdir -p "${PLAYWRIGHT_BROWSERS_PATH}" && \
    PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH}" python -m playwright install chromium

# Copy the entire application code into the Lambda task root
COPY . /var/task

# Set the default Lambda handler
CMD ["main.handler"]