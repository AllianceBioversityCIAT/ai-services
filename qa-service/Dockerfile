# Base image for AWS Lambda with Python 3.13 runtime
FROM public.ecr.aws/lambda/python:3.13

ARG PYTHONPATH=

ENV PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
    PYTHONPATH="${LAMBDA_TASK_ROOT}:${PYTHONPATH}" \
    PATH="/var/task/bin:${PATH}"

COPY requirements.txt .

# Install system libraries required by Playwright/Chromium (Amazon Linux base)
RUN yum install -y \
    alsa-lib \
    atk \
    at-spi2-atk \
    at-spi2-core \
    cairo \
    dbus-libs \
    expat \
    fontconfig \
    gtk3 \
    libX11 \
    libXcomposite \
    libXcursor \
    libXdamage \
    libXext \
    libXfixes \
    libXrandr \
    libXrender \
    libdrm \
    libxcb \
    libxkbcommon \
    mesa-libgbm \
    nspr \
    nss \
    nss-util \
    pango \
    systemd-libs \
    xorg-x11-server-Xvfb \
    && yum clean all && rm -rf /var/cache/yum

RUN pip install --no-cache-dir -r requirements.txt -t "${LAMBDA_TASK_ROOT}"


RUN mkdir -p "${PLAYWRIGHT_BROWSERS_PATH}" && \
    PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH}" python -m playwright install chromium



COPY . ${LAMBDA_TASK_ROOT}

# Set the default Lambda handler (file: main.py, function: handler)
CMD ["main.handler"]
