# Guía de Despliegue: ar-generator-service en AWS Lambda (Container Image)

Esta guía describe el proceso paso a paso para desplegar el servicio `ar-generator-service` en AWS Lambda usando una container image almacenada en Amazon ECR.

---

## Prerrequisitos

1. **AWS CLI** instalado y configurado
2. **Docker** instalado y funcionando
3. **Credenciales AWS** con permisos para:
   - ECR (crear repositorios, push imágenes)
   - Lambda (crear/actualizar funciones)
   - IAM (crear roles y políticas)
   - VPC (si se requiere conectividad a SQL Server)
   - Bedrock, S3, OpenSearch (según uso)

4. **Variables de entorno** configuradas o disponibles en AWS Secrets Manager

---

## Paso 1: Construir la Imagen Docker

Desde el directorio raíz del proyecto:

```bash
cd ar-generator-service
docker build -t ar-generator-service:latest .
```

**Verificación:**
```bash
docker images | grep ar-generator-service
```

Deberías ver la imagen listada.

---

## Paso 2: Obtener Account ID y Configurar Región

```bash
# Obtener Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account ID: $ACCOUNT_ID"

# Configurar región (ajusta según tu necesidad)
REGION="us-east-1"
echo "Region: $REGION"
```

---

## Paso 3: Login en Amazon ECR

```bash
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
```

**Salida esperada:**
```
Login Succeeded
```

---

## Paso 4: Crear Repositorio ECR (si no existe)

```bash
aws ecr create-repository \
    --repository-name ar-generator-service \
    --region $REGION \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256
```

**Si el repositorio ya existe**, verás un error. Eso está bien, continúa al siguiente paso.

**Obtener URI del repositorio:**
```bash
ECR_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/ar-generator-service"
echo "ECR URI: $ECR_URI"
```

---

## Paso 5: Tag de la Imagen

```bash
docker tag ar-generator-service:latest $ECR_URI:latest
docker tag ar-generator-service:latest $ECR_URI:$(date +%Y%m%d-%H%M%S)
```

Esto crea dos tags:
- `latest` - para despliegues rápidos
- Timestamp - para versionado específico

---

## Paso 6: Push a ECR

```bash
docker push $ECR_URI:latest
docker push $ECR_URI:$(date +%Y%m%d-%H%M%S)
```

**Nota:** El primer push puede tardar varios minutos dependiendo del tamaño de la imagen.

**Verificación:**
```bash
aws ecr describe-images --repository-name ar-generator-service --region $REGION
```

---

## Paso 7: Crear IAM Role para Lambda

### 7.1 Crear Trust Policy

Crea un archivo `lambda-trust-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### 7.2 Crear el Role

```bash
aws iam create-role \
    --role-name ar-generator-lambda-role \
    --assume-role-policy-document file://lambda-trust-policy.json
```

### 7.3 Adjuntar Políticas Básicas

```bash
# Política básica de ejecución Lambda
aws iam attach-role-policy \
    --role-name ar-generator-lambda-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Política para VPC (si se requiere conectividad a SQL Server)
aws iam attach-role-policy \
    --role-name ar-generator-lambda-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole
```

### 7.4 Crear Política Personalizada para Bedrock, S3, OpenSearch

Crea un archivo `lambda-custom-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:HeadObject"
      ],
      "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "es:ESHttpGet",
        "es:ESHttpPost",
        "es:ESHttpPut"
      ],
      "Resource": "arn:aws:es:*:*:domain/YOUR_OPENSEARCH_DOMAIN/*"
    }
  ]
}
```

**Reemplaza:**
- `YOUR_BUCKET_NAME` con el nombre de tu bucket S3
- `YOUR_OPENSEARCH_DOMAIN` con el nombre de tu dominio OpenSearch

**Crear y adjuntar la política:**
```bash
aws iam create-policy \
    --policy-name ar-generator-lambda-custom-policy \
    --policy-document file://lambda-custom-policy.json

aws iam attach-role-policy \
    --role-name ar-generator-lambda-role \
    --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/ar-generator-lambda-custom-policy
```

**Obtener ARN del Role:**
```bash
ROLE_ARN=$(aws iam get-role --role-name ar-generator-lambda-role --query 'Role.Arn' --output text)
echo "Role ARN: $ROLE_ARN"
```

---

## Paso 8: Crear Lambda Function

### 8.1 Crear la Función (Primera Vez)

```bash
aws lambda create-function \
    --function-name ar-generator-service \
    --package-type Image \
    --code ImageUri=$ECR_URI:latest \
    --role $ROLE_ARN \
    --timeout 900 \
    --memory-size 3008 \
    --region $REGION \
    --description "AICCRA Report Generator Service - Lambda Container Image"
```

### 8.2 Actualizar Función Existente

Si la función ya existe:

```bash
aws lambda update-function-code \
    --function-name ar-generator-service \
    --image-uri $ECR_URI:latest \
    --region $REGION
```

**Esperar a que la actualización complete:**
```bash
aws lambda wait function-updated \
    --function-name ar-generator-service \
    --region $REGION
```

---

## Paso 9: Configurar Variables de Entorno

```bash
aws lambda update-function-configuration \
    --function-name ar-generator-service \
    --environment Variables="{
        AWS_REGION=$REGION,
        SERVER=your-sql-server-host,
        DATABASE=your-database-name,
        CLIENT_ID=your-azure-client-id,
        CLIENT_SECRET=your-azure-client-secret,
        OPENSEARCH_HOST=your-opensearch-host,
        OPENSEARCH_INDEX_NAME=your-index-name,
        BUCKET_NAME=your-bucket-name
    }" \
    --region $REGION
```

**⚠️ IMPORTANTE:** Para secretos sensibles, usa **AWS Secrets Manager** en lugar de variables de entorno.

### 9.1 Usar Secrets Manager (Recomendado)

1. **Crear secretos:**
```bash
aws secretsmanager create-secret \
    --name ar-generator/sql-server \
    --secret-string '{"client_secret":"your-secret"}' \
    --region $REGION
```

2. **Actualizar código para leer de Secrets Manager:**
   - Ver sección de código modificado en este documento

---

## Paso 10: Configurar VPC (Si se Requiere SQL Server)

Si SQL Server está en una VPC privada:

```bash
aws lambda update-function-configuration \
    --function-name ar-generator-service \
    --vpc-config SubnetIds=subnet-xxx,subnet-yyy,SecurityGroupIds=sg-xxx \
    --region $REGION
```

**Reemplaza:**
- `subnet-xxx,subnet-yyy` con tus subnets privadas
- `sg-xxx` con tu security group

**Nota:** Lambda en VPC requiere NAT Gateway o VPC Endpoints para acceso a internet (Bedrock, S3, OpenSearch).

---

## Paso 11: Configurar API Gateway

### 11.1 Crear REST API

```bash
API_ID=$(aws apigateway create-rest-api \
    --name ar-generator-api \
    --description "API Gateway for ar-generator-service" \
    --region $REGION \
    --query 'id' --output text)

echo "API ID: $API_ID"
```

### 11.2 Crear Resource y Method

```bash
# Obtener root resource ID
ROOT_RESOURCE_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --region $REGION \
    --query 'items[?path==`/`].id' --output text)

# Crear resource para proxy
PROXY_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_RESOURCE_ID \
    --path-part '{proxy+}' \
    --region $REGION \
    --query 'id' --output text)

# Crear método ANY
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $PROXY_RESOURCE_ID \
    --http-method ANY \
    --authorization-type NONE \
    --region $REGION

# Integración Lambda
LAMBDA_ARN=$(aws lambda get-function \
    --function-name ar-generator-service \
    --region $REGION \
    --query 'Configuration.FunctionArn' --output text)

aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $PROXY_RESOURCE_ID \
    --http-method ANY \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations \
    --region $REGION

# Dar permiso a API Gateway para invocar Lambda
aws lambda add-permission \
    --function-name ar-generator-service \
    --statement-id apigateway-invoke \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn arn:aws:execute-api:$REGION:$ACCOUNT_ID:$API_ID/*/* \
    --region $REGION
```

### 11.3 Desplegar API

```bash
DEPLOYMENT_ID=$(aws apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name prod \
    --region $REGION \
    --query 'id' --output text)

API_URL="https://$API_ID.execute-api.$REGION.amazonaws.com/prod"
echo "API URL: $API_URL"
```

---

## Paso 12: Verificación

### 12.1 Health Check

```bash
curl $API_URL/health
```

**Respuesta esperada:**
```json
{
  "status": "healthy",
  "service": "AICCRA Report Generator API",
  "version": "1.0.0"
}
```

### 12.2 Probar Endpoint de Generación

```bash
curl -X POST $API_URL/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "indicator": "IPI 1.1",
    "year": 2025,
    "insert_data": false
  }'
```

---

## Paso 13: Monitoreo y Logs

### Ver Logs en CloudWatch

```bash
aws logs tail /aws/lambda/ar-generator-service --follow --region $REGION
```

### Ver Métricas

```bash
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Duration \
    --dimensions Name=FunctionName,Value=ar-generator-service \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 300 \
    --statistics Average,Maximum \
    --region $REGION
```

---

## Actualización de la Imagen (Re-deploy)

Para actualizar la función con una nueva versión de la imagen:

```bash
# 1. Build nueva imagen
docker build -t ar-generator-service:latest .

# 2. Tag
docker tag ar-generator-service:latest $ECR_URI:latest

# 3. Push
docker push $ECR_URI:latest

# 4. Actualizar Lambda
aws lambda update-function-code \
    --function-name ar-generator-service \
    --image-uri $ECR_URI:latest \
    --region $REGION

# 5. Esperar actualización
aws lambda wait function-updated \
    --function-name ar-generator-service \
    --region $REGION
```

---

## Troubleshooting

### Error: "Cannot connect to SQL Server"

**Causa:** Lambda no está en VPC o security group incorrecto.

**Solución:**
1. Verificar que Lambda está en VPC con subnets correctas
2. Verificar security group permite outbound TCP 1433
3. Verificar NAT Gateway o VPC Endpoints configurados

### Error: "ODBC Driver 18 not found"

**Causa:** Driver no instalado correctamente en imagen.

**Solución:**
1. Verificar Dockerfile incluye instalación de msodbcsql18
2. Rebuild imagen
3. Verificar con: `docker run --rm ar-generator-service:latest odbcinst -q -d`

### Error: "Timeout"

**Causa:** Operación excede 15 minutos.

**Solución:**
1. Usar `insert_data=false` para operaciones rápidas
2. Para operaciones largas, implementar arquitectura asíncrona (Step Functions)

### Error: "Permission denied" en /tmp

**Causa:** Permisos incorrectos en /tmp.

**Solución:**
- /tmp tiene permisos correctos por defecto en Lambda
- Verificar que código usa `/tmp` explícitamente

---

## Configuración Recomendada

### Lambda Settings

- **Timeout:** 900 segundos (15 minutos - máximo)
- **Memory:** 3008 MB (máximo para mejor performance con pandas)
- **Reserved Concurrency:** 5 (ajustar según necesidad)
- **Ephemeral Storage:** 10240 MB (máximo para /tmp)

### VPC Configuration

- **Subnets:** Mínimo 2 subnets privadas en diferentes AZs
- **Security Groups:** Outbound TCP 1433 (SQL Server), TCP 443 (HTTPS)
- **NAT Gateway:** Requerido para acceso a internet

---

## Costos Estimados

- **Lambda:** ~$0.0000166667 por GB-segundo
- **ECR:** ~$0.10 por GB/mes de almacenamiento
- **API Gateway:** $3.50 por millón de requests
- **NAT Gateway:** ~$32/mes + data transfer

---

## Soporte

Para problemas o preguntas:
- Revisar logs en CloudWatch
- Verificar configuración de IAM Role
- Validar variables de entorno
- Contactar: [Definir contacto]

---

**Última actualización:** 2025-01-XX
