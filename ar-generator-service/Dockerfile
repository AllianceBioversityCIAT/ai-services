# Use the official AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.13

# Install system dependencies required for pyodbc and ODBC Driver 18
# Note: Lambda Python 3.13 uses Amazon Linux 2023 which uses dnf instead of yum
RUN dnf update -y && \
    dnf install -y \
    unixODBC \
    unixODBC-devel \
    curl \
    tar \
    gcc-c++ \
    python3-devel \
    && dnf clean all

# Install Microsoft ODBC Driver 18 for SQL Server
# Amazon Linux 2023 is compatible with RHEL 8 packages
RUN curl https://packages.microsoft.com/config/rhel/8/prod.repo > /etc/yum.repos.d/mssql-release.repo && \
    ACCEPT_EULA=Y dnf install -y msodbcsql18 && \
    dnf clean all

# Verify ODBC Driver installation
RUN odbcinst -q -d

# Copy requirements file
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ${LAMBDA_TASK_ROOT}/app
COPY db_conn ${LAMBDA_TASK_ROOT}/db_conn
COPY api_server.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler
CMD [ "api_server.handler" ]
