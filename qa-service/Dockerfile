# Base image for AWS Lambda with Python 3.13 runtime
FROM public.ecr.aws/lambda/python:3.13

# Install required system dependencies for Playwright Chromium
RUN microdnf update && \
    microdnf install -y \
    alsa-lib \
    atk \
    at-spi2-atk \
    cups-libs \
    GConf2 \
    gtk3 \
    libX11 \
    libXcomposite \
    libXcursor \
    libXdamage \
    libXext \
    libXi \
    libXrandr \
    libXScrnSaver \
    libXtst \
    pango \
    xorg-x11-fonts-100dpi \
    xorg-x11-fonts-75dpi \
    xorg-x11-utils \
    xorg-x11-fonts-Type1 \
    xorg-x11-fonts-misc \
    libdrm \
    libgbm \
    ipa-gothic-fonts \
    && microdnf clean all

# Playwright paths
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt -t "${LAMBDA_TASK_ROOT}"

# Install Chromium browser for Playwright
RUN mkdir -p "${PLAYWRIGHT_BROWSERS_PATH}" && \
    PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH}" python -m playwright install chromium

COPY . ${LAMBDA_TASK_ROOT}

CMD ["main.handler"]
