FROM python:3.10-bullseye
WORKDIR /app

# ── Dependencias básicas + unixODBC ──────────────────────────
RUN apt-get update && \
    apt-get install -y curl gnupg gcc g++ \
    unixodbc unixodbc-dev \
    libgssapi-krb5-2 libldap-2.4-2 \
    libssl-dev libcurl4 libstdc++6

# ── Clave y repositorio de Microsoft ─────────────────────────
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
    | gpg --dearmor -o /usr/share/keyrings/microsoft.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] \
    https://packages.microsoft.com/repos/microsoft-debian-bullseye-prod bullseye main" \
    > /etc/apt/sources.list.d/mssql-release.list

# ── Driver ODBC 18 y herramientas ────────────────────────────
RUN apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql18 mssql-tools18 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ── Instalación de librerías Python ─────────────────────────
RUN pip install --no-cache-dir pyodbc==4.0.39 requests

# ── Código de la app ─────────────────────────────────────────
COPY . .
CMD ["python", "-u", "check_fabric.py"]