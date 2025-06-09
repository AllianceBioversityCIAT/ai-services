FROM public.ecr.aws/lambda/python:3.11

COPY app/ app/
COPY main.py ./ 
COPY .env ./
COPY requirements.txt .

RUN yum install -y gcc python3-devel
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

CMD ["main.handler"]