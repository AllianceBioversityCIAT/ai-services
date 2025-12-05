# Use Amazon Linux 2023 base image (has system libraries for Chromium)
FROM public.ecr.aws/amazonlinux/amazonlinux:2023

# Install Python 3.13 and system dependencies for Playwright/Chromium
RUN dnf update -y && \
    dnf install -y \
        python3.13 \
        python3.13-pip \
        python3.13-devel \
        libnspr \
        nss \
        nss-util \
        dbus \
        at-spi2-atk \
        libxkbcommon \
        libxcb \
        libX11 \
        libXcomposite \
        libXdamage \
        libXext \
        libXfixes \
        libXrandr \
        libgbm \
        libudev \
        alsa-lib \
    && dnf clean all

# Create Lambda task root directory structure
ENV LAMBDA_TASK_ROOT=/var/task \
    PYTHONPATH=/var/task:$PYTHONPATH \
    PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers

# Copy dependency file first to take advantage of Docker layer caching
COPY requirements.txt .

# Install Python dependencies into the Lambda task root
RUN pip3.13 install --no-cache-dir -r requirements.txt -t "${LAMBDA_TASK_ROOT}"

# Install Playwright Chromium browsers
RUN mkdir -p "${PLAYWRIGHT_BROWSERS_PATH}" && \
    PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH}" \
    /usr/bin/python3.13 -m playwright install chromium

# Copy the entire application code into the Lambda task root
COPY . ${LAMBDA_TASK_ROOT}

# Set the working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Define the handler using Mangum (ASGI adapter for Lambda)
CMD ["main.handler"]