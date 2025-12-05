# Builder con dependencias del sistema
FROM public.ecr.aws/sam/build-python3.13 as builder

# Instalar solo dependencias mínimas de Playwright
RUN dnf install -y \
    alsa-lib \
    atk \
    cairo \
    cups-libs \
    dbus-libs \
    expat \
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
    libnspr \
    libnss3 \
    libstdc++ \
    mesa-libEGL \
    pango \
    && dnf clean all

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install chromium --with-deps

# Runtime final para Lambda (scratch)
FROM public.ecr.aws/lambda/python:3.13

# Copiar Python site-packages y browsers
COPY --from=builder /usr/lib64 /usr/lib64
COPY --from=builder /usr/lib /usr/lib  
COPY --from=builder /usr/share/fonts /usr/share/fonts
COPY --from=builder /build/* ${LAMBDA_TASK_ROOT}/
COPY --from=builder /ms-playwright ${LAMBDA_TASK_ROOT}/ms-playwright

ENV PLAYWRIGHT_BROWSERS_PATH=${LAMBDA_TASK_ROOT}/ms-playwright

COPY . ${LAMBDA_TASK_ROOT}
CMD ["main.handler"]