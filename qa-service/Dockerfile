FROM public.ecr.aws/lambda/python:3.13

# Default PYTHONPATH keeps Docker build from warning about an undefined var while
# still appending the Lambda task root at runtime.
ARG PYTHONPATH=
ENV PLAYWRIGHT_BROWSERS_PATH=/tmp/pw-browsers \
    PYTHONPATH="${LAMBDA_TASK_ROOT}:${PYTHONPATH}" \
    PATH="/var/task/bin:${PATH}"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -t "${LAMBDA_TASK_ROOT}"

# Install Chromium binaries in a path Lambda can read. The base image lacks
# apt-get, so skip install-deps and rely on the Amazon Linux libraries already
# included in the Lambda runtime.
RUN mkdir -p "${PLAYWRIGHT_BROWSERS_PATH}" && \
    python -m playwright install chromium

COPY app/ app/
COPY main.py ./
COPY .env ./
COPY . ${LAMBDA_TASK_ROOT}

CMD ["main.handler"]
