FROM public.ecr.aws/lambda/python:3.13

# Install dependencies into the Lambda task root
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -t "${LAMBDA_TASK_ROOT}"

# Application code (package layout must match local imports: api, ai, modules, utils)
COPY api/ ${LAMBDA_TASK_ROOT}/api/
COPY ai/ ${LAMBDA_TASK_ROOT}/ai/
COPY modules/ ${LAMBDA_TASK_ROOT}/modules/
COPY utils/ ${LAMBDA_TASK_ROOT}/utils/
COPY main.py ${LAMBDA_TASK_ROOT}/

# Mangum ASGI handler exported from main.py
CMD ["main.handler"]
