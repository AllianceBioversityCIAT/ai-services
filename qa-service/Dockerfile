# Base image for AWS Lambda with Python 3.13 runtime
FROM public.ecr.aws/lambda/python:3.13

# Env vars
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
    PYTHONPATH="${LAMBDA_TASK_ROOT}:${PYTHONPATH}"

# (Opcional, pero ordenado)
WORKDIR ${LAMBDA_TASK_ROOT}

# 1) Instalar dependencias de sistema para Chromium
# En Amazon Linux normalmente funciona yum; si diera error, cambiar por microdnf
RUN yum update -y && \
    yum install -y \
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
    && yum clean all && rm -rf /var/cache/yum

# 2) Dependencias Python
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt -t "${LAMBDA_TASK_ROOT}"

# 3) Instalar Chromium de Playwright en /opt (layer interna del contenedor)
RUN mkdir -p "${PLAYWRIGHT_BROWSERS_PATH}" && \
    PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH}" python -m playwright install chromium

# 4) Copiar el código de la app
COPY . ${LAMBDA_TASK_ROOT}

# 5) Handler por defecto de Lambda
CMD ["main.handler"]
