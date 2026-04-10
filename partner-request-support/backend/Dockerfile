# Partner Request Support - Backend API for AWS Lambda (container image)
# Handler: Mangum wrapping FastAPI (main.handler)
FROM public.ecr.aws/lambda/python:3.13

RUN dnf update -y && dnf install -y gcc python3-devel && dnf clean all

COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements.txt

COPY api.py main.py ${LAMBDA_TASK_ROOT}/
COPY config ${LAMBDA_TASK_ROOT}/config
COPY logger ${LAMBDA_TASK_ROOT}/logger
COPY src ${LAMBDA_TASK_ROOT}/src

CMD [ "main.handler" ]
