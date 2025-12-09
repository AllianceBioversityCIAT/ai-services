# Base image for AWS Lambda with Python 3.13 runtime
FROM public.ecr.aws/lambda/python:3.13

# Env vars
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
    PYTHONPATH="${LAMBDA_TASK_ROOT}"

WORKDIR ${LAMBDA_TASK_ROOT}

# 1) Instalar dependencias de sistema para Chromium en AL2023 (usa dnf/microdnf)
RUN dnf update -y && \
    dnf install -y \
    atk \
    cups-libs \
    libdrm \
    libXcomposite \
    libXdamage \
    libXrandr \
    libXfixes \
    libXcursor \
    libXi \
    libXtst \
    pango \
    alsa-lib \
    libX11 \
    libXext \
    libXrender \
    libXScrnSaver \
    nss \
    mesa-libgbm \
    xorg-x11-fonts-Type1 \
    xorg-x11-fonts-misc \
    && dnf clean all && rm -rf /var/cache/dnf
# 👆 Si algún paquete no existe, lo puedes quitar de la lista y volver a build

# 2) Python deps
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt -t "${LAMBDA_TASK_ROOT}"

# 3) Instalar Chromium de Playwright en /opt
RUN mkdir -p "${PLAYWRIGHT_BROWSERS_PATH}" && \
    PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH}" python -m playwright install chromium

# 4) Copiar código
COPY . ${LAMBDA_TASK_ROOT}

# 5) Handler por defecto
CMD ["main.handler"]
