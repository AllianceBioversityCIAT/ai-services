FROM public.ecr.aws/lambda/python:3.13

COPY app/ app/
COPY main.py ./ 
COPY .env ./
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -t "${LAMBDA_TASK_ROOT}"

# Install Playwright dependencies and Chromium in /tmp for Lambda
RUN playwright install-deps chromium && \
    PLAYWRIGHT_BROWSERS_PATH=/tmp/pw-browsers playwright install chromium

COPY . ${LAMBDA_TASK_ROOT}

CMD ["main.handler"]