FROM public.ecr.aws/lambda/python:3.13

ARG PYTHONPATH=
ENV PLAYWRIGHT_BROWSERS_PATH=/tmp/pw-browsers \
    PYTHONPATH="${LAMBDA_TASK_ROOT}:${PYTHONPATH}" \
    PATH="/var/task/bin:${PATH}"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -t "${LAMBDA_TASK_ROOT}"

RUN mkdir -p "${PLAYWRIGHT_BROWSERS_PATH}" && \
    python -m playwright install chromium

COPY app/ app/
COPY main.py ./
COPY .env ./
COPY . ${LAMBDA_TASK_ROOT}

CMD ["main.handler"]