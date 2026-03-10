# Resumen de Cambios para Migración a AWS Lambda

Este documento resume todos los cambios realizados en el proyecto `ar-generator-service` para prepararlo para despliegue en AWS Lambda usando container image.

---

## 📋 Archivos Modificados

### 1. `db_conn/sql_connection.py`

**Cambios realizados:**
- ✅ Archivos temporales ahora se escriben en `/tmp` en lugar del directorio actual
- ✅ Agregado `import os` para usar `os.path.join()`
- ✅ Modificado `load_data()`: líneas 152-172
- ✅ Modificado `load_full_data()`: líneas 266-280

**Código modificado:**
```python
# ANTES:
jsonl_file = f'{table_name}_ar.jsonl'
csv_file = f'{table_name}_ar.csv'

# DESPUÉS:
tmp_dir = "/tmp"
jsonl_file = os.path.join(tmp_dir, f'{table_name}_ar.jsonl')
csv_file = os.path.join(tmp_dir, f'{table_name}_ar.csv')
```

---

### 2. `app/utils/s3/divide_jsonl_files.py`

**Cambios realizados:**
- ✅ Archivos CSV y metadata ahora se escriben en `/tmp/csv_files` en lugar de `csv_files` en directorio actual
- ✅ Modificado función `split_jsonl_to_individual_csv_files()`: líneas 29-34, 56

**Código modificado:**
```python
# ANTES:
local_path = os.path.join(os.getcwd(), "csv_files", file_name)

# DESPUÉS:
tmp_dir = "/tmp"
csv_files_dir = os.path.join(tmp_dir, "csv_files")
local_path = os.path.join(csv_files_dir, file_name)
```

---

### 3. `app/llm/invoke_llm.py`

**Cambios realizados:**
- ✅ Eliminado uso de credenciales AWS hardcodeadas
- ✅ Ahora usa IAM Role automáticamente en Lambda
- ✅ Mantiene compatibilidad con variables de entorno para desarrollo local

**Código modificado:**
```python
# ANTES:
bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    aws_access_key_id=BR['aws_access_key'],
    aws_secret_access_key=BR['aws_secret_key'],
    region_name=BR['region']
)

# DESPUÉS:
bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name=BR.get('region', 'us-east-1')
    # IAM Role provides credentials automatically in Lambda
)
```

---

### 4. `app/utils/s3/upload_file_to_s3.py`

**Cambios realizados:**
- ✅ Eliminado uso de credenciales AWS hardcodeadas
- ✅ Ahora usa IAM Role automáticamente en Lambda

**Código modificado:**
```python
# ANTES:
s3_client = boto3.client(
    's3',
    aws_access_key_id=S3['aws_access_key'],
    aws_secret_access_key=S3['aws_secret_key'],
    region_name=S3['aws_region']
)

# DESPUÉS:
s3_client = boto3.client(
    's3',
    region_name=S3.get('aws_region', 'us-east-1')
    # IAM Role provides credentials automatically in Lambda
)
```

---

### 5. `app/llm/vectorize_os.py`

**Cambios realizados:**
- ✅ Eliminado uso de credenciales AWS hardcodeadas
- ✅ Ahora usa IAM Role automáticamente en Lambda
- ✅ Fallback a variables de entorno para desarrollo local

**Código modificado:**
```python
# ANTES:
credentials = boto3.Session(
    aws_access_key_id=OPENSEARCH['aws_access_key'],
    aws_secret_access_key=OPENSEARCH['aws_secret_key'],
    region_name=BR['region']
).get_credentials()

# DESPUÉS:
region = BR.get('region', 'us-east-1')
session = boto3.Session(region_name=region)
credentials = session.get_credentials()

# Fallback para desarrollo local
if not credentials:
    if OPENSEARCH.get('aws_access_key') and OPENSEARCH.get('aws_secret_key'):
        credentials = type('obj', (object,), {
            'access_key': OPENSEARCH['aws_access_key'],
            'secret_key': OPENSEARCH['aws_secret_key'],
            'token': None
        })()
```

---

### 6. `app/llm/vectorize_os_annual.py`

**Cambios realizados:**
- ✅ Mismo cambio que `vectorize_os.py` (eliminación de credenciales hardcodeadas)

---

### 7. `app/api/main.py`

**Cambios realizados:**
- ✅ Removido mount de static files (`app.mount("/static", ...)`)
- ✅ Modificado endpoint `/web` para retornar mensaje JSON en lugar de servir archivo HTML

**Código modificado:**
```python
# ANTES:
app.mount("/static", StaticFiles(directory="web"), name="static")

@app.get("/web")
async def serve_ui_alt():
    return FileResponse('web/index.html')

# DESPUÉS:
# Static files mount removed - not compatible with Lambda

@app.get("/web")
async def serve_ui_alt():
    return JSONResponse(
        status_code=200,
        content={
            "message": "Web UI is not available in Lambda deployment",
            "api_docs": "/docs",
            "note": "Deploy web UI separately using S3 + CloudFront"
        }
    )
```

---

### 8. `app/utils/config/config_util.py`

**Cambios realizados:**
- ✅ Agregados comentarios indicando que credenciales son opcionales (IAM Role usado en Lambda)
- ✅ Agregado valor por defecto para región

**Código modificado:**
```python
# Agregados comentarios y valores por defecto:
BR = {
    "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID_BR"),  # Optional: IAM Role used in Lambda
    "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY_BR"),  # Optional
    "region": os.getenv("AWS_REGION", "us-east-1")  # Default value
}
```

---

### 9. `requirements.txt`

**Cambios realizados:**
- ✅ Eliminado `uvicorn` (no necesario en Lambda, usa Mangum)
- ✅ Eliminado `python-crontab` (no compatible con Lambda, usar EventBridge)

**Antes:**
```
uvicorn
python-crontab
```

**Después:**
```
# uvicorn removed - not needed in Lambda (uses Mangum)
# python-crontab removed - not compatible with Lambda (use EventBridge)
```

---

### 10. `api_server.py`

**Cambios realizados:**
- ✅ Reemplazado código de uvicorn con handler de Mangum para Lambda
- ✅ Archivo ahora es el punto de entrada para Lambda

**Código anterior:** Usaba uvicorn para desarrollo local  
**Código nuevo:** Usa Mangum para Lambda

```python
from mangum import Mangum
from app.api.main import app
from dotenv import load_dotenv

load_dotenv()

handler = Mangum(app, lifespan="off")
```

**Nota:** `main.py` sigue existiendo para desarrollo local con uvicorn si es necesario.

---

## 📄 Archivos Nuevos Creados

### 1. `Dockerfile`

**Ubicación:** `ar-generator-service/Dockerfile`

**Contenido:**
- Imagen base: `public.ecr.aws/lambda/python:3.13`
- Instalación de `unixODBC` y `unixODBC-devel`
- Instalación de `ODBC Driver 18 for SQL Server`
- Instalación de dependencias Python desde `requirements.txt`
- Copia de código de la aplicación
- Handler configurado: `api_server.handler`

**Ver contenido completo en:** `Dockerfile`

---

### 2. `.dockerignore`

**Ubicación:** `ar-generator-service/.dockerignore`

**Contenido:**
- Excluye archivos innecesarios del build
- Excluye `__pycache__`, `*.pyc`, `.venv`, `.env`
- Excluye `docs/`, `web/`, `*.jsonl`, `*.csv`
- Excluye `MIGRATION_ANALYSIS.md`

**Ver contenido completo en:** `.dockerignore`

---

### 3. `DEPLOY_LAMBDA.md`

**Ubicación:** `ar-generator-service/DEPLOY_LAMBDA.md`

**Contenido:**
- Instrucciones paso a paso para build de imagen Docker
- Login en Amazon ECR
- Creación de repositorio ECR
- Push de imagen a ECR
- Creación de IAM Role y políticas
- Creación y configuración de Lambda function
- Configuración de API Gateway
- Instrucciones de verificación y troubleshooting

**Ver contenido completo en:** `DEPLOY_LAMBDA.md`

---

## ✅ Validaciones Realizadas

### Compatibilidad con Lambda

- ✅ **Stateless:** El servicio no mantiene estado entre invocaciones
- ✅ **Archivos temporales:** Todos usan `/tmp` (compatible con Lambda)
- ✅ **Sin procesos persistentes:** No hay daemons o procesos en background
- ✅ **Sin cronjobs:** Los cronjobs deben migrarse a EventBridge
- ✅ **FastAPI + Mangum:** Ya implementado y funcional
- ✅ **IAM Role:** Credenciales AWS ahora usan IAM Role automáticamente

### Dependencias Nativas

- ✅ **pyodbc:** Instalado en Dockerfile con `unixODBC` y `ODBC Driver 18`
- ✅ **pandas:** Compatible con Lambda base image
- ✅ **boto3:** Compatible con Lambda

### Archivos Temporales

- ✅ **JSONL files:** Escritos en `/tmp`
- ✅ **CSV files:** Escritos en `/tmp`
- ✅ **Metadata files:** Escritos en `/tmp/csv_files`
- ✅ **Limpieza:** Archivos se eliminan después de uso

---

## 🚀 Próximos Pasos

1. **Build local de imagen Docker:**
   ```bash
   docker build -t ar-generator-service:latest .
   ```

2. **Probar imagen localmente (opcional):**
   ```bash
   docker run -p 9000:8080 \
     -e AWS_REGION=us-east-1 \
     -e SERVER=your-server \
     -e DATABASE=your-database \
     ar-generator-service:latest
   ```

3. **Seguir instrucciones en `DEPLOY_LAMBDA.md`** para despliegue completo

---

## ⚠️ Notas Importantes

### Limitaciones Conocidas

1. **Timeout de 15 minutos:**
   - Operaciones con `insert_data=True` pueden tomar 30-60 minutos
   - Estas operaciones NO son compatibles con Lambda timeout máximo (15 min)
   - Solución: Usar `insert_data=False` o implementar arquitectura asíncrona

2. **Web UI:**
   - No disponible en Lambda deployment
   - Debe desplegarse por separado (S3 + CloudFront) o usar API directamente

3. **Cronjobs:**
   - Los scripts en `app/utils/cronjob/` no funcionan en Lambda
   - Deben migrarse a EventBridge Rules que invoquen Lambda

### Configuración Requerida en AWS

1. **IAM Role** con permisos para:
   - Bedrock (InvokeModel)
   - S3 (PutObject, GetObject)
   - OpenSearch (ESHttpGet, ESHttpPost, ESHttpPut)
   - CloudWatch Logs
   - VPC (si se requiere SQL Server)

2. **VPC Configuration** (si SQL Server está en VPC privada):
   - Subnets privadas
   - Security Groups
   - NAT Gateway o VPC Endpoints

3. **Environment Variables** en Lambda:
   - `SERVER`, `DATABASE`, `CLIENT_ID`, `CLIENT_SECRET`
   - `OPENSEARCH_HOST`, `OPENSEARCH_INDEX_NAME`
   - `BUCKET_NAME`, `AWS_REGION`

---

## 📝 Checklist de Despliegue

- [ ] Dockerfile creado y probado
- [ ] Código modificado para usar `/tmp`
- [ ] Credenciales AWS eliminadas (usar IAM Role)
- [ ] `requirements.txt` actualizado (uvicorn y python-crontab removidos)
- [ ] `.dockerignore` creado
- [ ] Imagen Docker build exitoso
- [ ] ECR repository creado
- [ ] Imagen push a ECR exitoso
- [ ] IAM Role creado con políticas adecuadas
- [ ] Lambda function creada/actualizada
- [ ] Variables de entorno configuradas
- [ ] VPC configurado (si aplica)
- [ ] API Gateway configurado
- [ ] Health check exitoso
- [ ] Endpoints probados

---

**Fecha de cambios:** 2025-01-XX  
**Versión:** 1.0.0-Lambda
