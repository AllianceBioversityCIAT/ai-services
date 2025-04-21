
# Use Python 3.11 slim as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies + pipx + uv + cron + supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libffi-dev libssl-dev curl pipx cron supervisor \
    && pipx ensurepath \
    && pipx install uv \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Ensure logs and cron directories exist
RUN mkdir -p /app/data/logs /etc/cron.d

# Install dependencies using uv in system environment
RUN /root/.local/bin/uv pip install --system -r pyproject.toml

# Set up the cron job (cron job installation)
RUN python app/utils/cronjob/setup_db_cleaner_cron.py install

# Expose port if needed
EXPOSE 8000

# Add Supervisor configuration to run both the cron job and the app
COPY supervisord.conf /etc/supervisor/supervisord.conf

# Run supervisord to start both cron and the app
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]