# Builder con dependencias mínimas
FROM public.ecr.aws/sam/build-python3.13 as builder

WORKDIR /build

# Instalar SOLO dependencias gráficas esenciales (sin libnspr/libnss3)
RUN dnf install -y \
    alsa-lib \
    atk \
    cairo \
    cups-libs \
    dbus-libs \
    fontconfig \
    freetype \
    glib2 \
    gtk3 \
    libX11 \
    libXcomposite \
    libXcursor \
    libXdamage \
    libXext \
    libXfixes \
    libXi \
    libXrandr \
    libXrender \
    libdrm \
    libgbm \
    mesa-libEGL \
    pango \
    nspr \
    nss \
    && dnf clean all

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install --with-deps chromium

# Runtime final Lambda
FROM public.ecr.aws/lambda/python:3.13

# Copiar libs esenciales
COPY --from=builder /usr/lib64 /usr/lib64
COPY --from=builder /usr/lib /usr/lib
COPY --from=builder /usr/share/fonts /usr/share/fonts

# Copiar Python packages y Playwright browsers
COPY --from=builder /build ${LAMBDA_TASK_ROOT}
COPY --from=builder /ms-playwright ${LAMBDA_TASK_ROOT}/ms-playwright

ENV PLAYWRIGHT_BROWSERS_PATH=${LAMBDA_TASK_ROOT}/ms-playwright \
    PATH="${LAMBDA_TASK_ROOT}/bin:${PATH}"

COPY . ${LAMBDA_TASK_ROOT}
CMD ["main.handler"]
