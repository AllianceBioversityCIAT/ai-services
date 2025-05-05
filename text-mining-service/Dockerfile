FROM public.ecr.aws/lambda/python:3.11

COPY app/ app/
COPY main.py ./
COPY .env ./

COPY requirements.txt .
RUN pip install -r requirements.txt

CMD ["main.handler"]

