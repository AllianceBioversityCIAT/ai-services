# 🚀 Guía Rápida - CLARISA Mapping

## Setup Rápido (5 pasos)

### 1️⃣ Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 2️⃣ Configurar Variables de Entorno

```bash
# Copiar el archivo de ejemplo
cp .env.example .env

# Editar .env con tus credenciales
nano .env  # o usa tu editor favorito
```

**Variables requeridas:**
- `CLARISA_API_URL` - URL de la API de CLARISA
- `SUPABASE_URL` - URL de tu proyecto Supabase
- `SUPABASE_KEY` - Key de Supabase (anon o service role)
- `AWS_ACCESS_KEY_ID_BR` - AWS Access Key (para Bedrock)
- `AWS_SECRET_ACCESS_KEY_BR` - AWS Secret Key (para Bedrock)

### 3️⃣ Crear la Tabla en Supabase

1. Abre el **SQL Editor** en Supabase
2. Copia y pega el contenido de `sql/create_clarisa_vector_table.sql`
3. Ejecuta el script

Esto creará:
- ✅ Tabla `clarisa_institutions_v2`
- ✅ Índices vectoriales (ivfflat)
- ✅ 3 funciones RPC para búsqueda

### 4️⃣ Poblar la Base de Datos

```bash
python populate_clarisa_db.py
```

**Tiempo estimado:** 10-15 minutos

Este script:
1. Descarga ~3000+ instituciones de CLARISA
2. Genera embeddings con Amazon Titan (1024 dims)
3. Inserta en Supabase en batches

### 5️⃣ Probar la Búsqueda

```bash
python search_example.py
```

Verás 4 ejemplos de búsqueda híbrida en acción.

---

## 📖 Uso Básico

### Búsqueda Simple

```python
from search_example import search_institution_hybrid

# Buscar por nombre
result = search_institution_hybrid(
    partner_name="Wageningen University",
    threshold=0.4
)

print(result['name'])
print(result['final_score'])
```

### Búsqueda con Acrónimo

```python
result = search_institution_hybrid(
    partner_name="World Resources Institute",
    acronym="WRI",
    threshold=0.4
)
```

---

## 🔍 Cómo Funciona la Búsqueda Híbrida

```
Query: "Wageningen University"
    ↓
1. Generar Embedding (Titan) - SIN normalizar
   "Wageningen University" → [0.123, 0.456, ...]
    ↓
2. Buscar Top 5 por Similitud Coseno (Supabase RPC)
   Los embeddings en DB también están SIN normalizar
    ↓
3. Desempate con RapidFuzz - CON normalización
   "wageningen university" vs "wageningen university and research"
    ↓
Score Final = 50% Coseno + 40% Fuzz Name + 10% Fuzz Acronym
    ↓
Mejor Match ✨
```

### 📝 Estrategia de Normalización

**Clave:** Usamos **dos niveles** de normalización:

| Contexto | Normalización | Función |
|----------|---------------|---------|
| **Embeddings** | ❌ Mínima | Preserva semántica |
| **RapidFuzz** | ✅ Completa | Mejora string matching |

```python
# Para embeddings (guardado en DB)
"Wageningen University and Research Centre (WUR)"  # Original

# Para RapidFuzz (al comparar)
"wageningen university and research centre wur"   # Normalizado
```

**Ver:** [docs/NORMALIZATION_STRATEGY.md](docs/NORMALIZATION_STRATEGY.md) para más detalles.

---

## 📁 Archivos Clave

| Archivo | Propósito |
|---------|-----------|
| `populate_clarisa_db.py` | Poblar la base de datos |
| `search_example.py` | Ejemplos de búsqueda |
| `src/clarisa_api.py` | Cliente API de CLARISA |
| `src/embeddings.py` | Generar embeddings con Titan |
| `src/supabase_client.py` | Funciones de Supabase |
| `sql/create_clarisa_vector_table.sql` | Crear tabla en Supabase |

---

## ⚙️ Configuración Avanzada

### Ajustar Pesos de Búsqueda

En `search_example.py`, modifica:

```python
# Score combinado
combined_score = (
    0.50 * cosine_sim +      # ← Ajusta este peso
    0.40 * fuzz_name +       # ← Ajusta este peso
    0.10 * fuzz_acronym      # ← Ajusta este peso
)
```

### Cambiar Threshold

```python
# Más restrictivo (menos resultados, mayor precisión)
result = search_institution_hybrid(partner_name="...", threshold=0.7)

# Más permisivo (más resultados, menor precisión)
result = search_institution_hybrid(partner_name="...", threshold=0.3)
```

---

## 🐛 Problemas Comunes

### ❌ ImportError: No module named 'src'

```bash
# Asegúrate de estar en el directorio raíz del proyecto
cd clarisa-cgspace_mapping

# Ejecuta desde ahí
python populate_clarisa_db.py
```

### ❌ Supabase: relation "clarisa_institutions_v2" does not exist

Ejecuta el script SQL primero (Paso 3).

### ❌ AWS Bedrock: Access Denied

1. Verifica que tu usuario AWS tenga permisos para Bedrock
2. Confirma que la región sea `us-east-1`
3. Verifica que tengas acceso al modelo `amazon.titan-embed-text-v2:0`

### ❌ La tabla está vacía

Ejecuta `python populate_clarisa_db.py` primero.

---

## 📊 Verificar Estado

```python
from src.supabase_client import count_institutions

count = count_institutions()
print(f"Instituciones en la DB: {count}")
```

---

## 📚 Más Información

Ver [README.md](README.md) para documentación completa.

---

✅ **¡Listo para empezar!**
