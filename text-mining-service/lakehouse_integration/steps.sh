docker build --no-cache -t fabric-check .
docker run --env-file .env fabric-check