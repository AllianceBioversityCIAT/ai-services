FROM public.ecr.aws/lambda/python:3.13

COPY app/ app/
COPY main.py ./ 
COPY .env ./
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -t "${LAMBDA_TASK_ROOT}"

COPY . ${LAMBDA_TASK_ROOT}

CMD ["main.handler"]