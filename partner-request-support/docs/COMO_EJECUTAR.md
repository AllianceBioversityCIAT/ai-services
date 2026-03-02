# 🚀 Cómo Ejecutar el Mapeo de Instituciones

## 📋 Resumen

Este script procesa un archivo Excel con instituciones y las mapea automáticamente a CLARISA usando búsqueda híbrida (embeddings vectoriales + RapidFuzz).

---

## ✅ Prerequisitos

### 1. Base de datos poblada

```bash
# Si aún no lo has hecho
python populate_clarisa_db.py
```

Esto debe haber creado ~10,000+ instituciones en Supabase con sus embeddings.

### 2. Archivo Excel preparado

Tu Excel debe tener **al menos 3 columnas** en este orden:

| Columna | Nombre        | Requerido | Descripción                    |
|---------|---------------|-----------|--------------------------------|
| 0       | ID            | No        | Identificador (ej: cgspace_id) |
| 1       | partner_name  | **SÍ**    | Nombre de la institución       |
| 2       | acronym       | No        | Acrónimo (ej: WUR, MIT)        |

**Ejemplo:**

| id  | partner_name                            | acronym |
|-----|-----------------------------------------|---------|
| 123 | Wageningen University and Research      | WUR     |
| 456 | Massachusetts Institute of Technology   | MIT     |
| 789 | World Resources Institute               | WRI     |

---

## 🎯 Ejecutar el Pipeline

### Paso 1: Configurar el archivo Excel

Edita [mapping_clarisa_comparison.py](mapping_clarisa_comparison.py) línea ~265:

```python
excel_file = "File To Dani (1).xlsx"  # ← Cambia esto por tu archivo
```

### Paso 2: Ejecutar

```bash
python mapping_clarisa_comparison.py
```

### Paso 3: Revisar resultados

El script generará: `clarisa_mapping_results.xlsx`

---

## 📊 Output del Excel

El archivo de resultados incluirá las columnas originales MÁS:

| Columna               | Descripción                                    |
|-----------------------|------------------------------------------------|
| `MATCH_FOUND`         | True/False - si se encontró match              |
| `CLARISA_ID`          | ID de CLARISA del match                        |
| `CLARISA_NAME`        | Nombre completo de la institución en CLARISA   |
| `CLARISA_ACRONYM`     | Acrónimo en CLARISA                            |
| `CLARISA_COUNTRIES`   | Países donde opera                             |
| `CLARISA_TYPE`        | Tipo de institución                            |
| `CLARISA_WEBSITE`     | Sitio web                                      |
| `COSINE_SIMILARITY`   | Score de similitud vectorial (0-1)             |
| `FUZZ_NAME_SCORE`     | Score de similitud de texto nombre (0-1)       |
| `FUZZ_ACRONYM_SCORE`  | Score de similitud de texto acrónimo (0-1)     |
| `FINAL_SCORE`         | Score combinado final (0-1)                    |
| `MATCH_QUALITY`       | excellent/good/fair/no_match                   |

---

## ⚙️ Configuración Avanzada

Puedes ajustar los parámetros al inicio de [mapping_clarisa_comparison.py](mapping_clarisa_comparison.py):

```python
# Líneas 18-26
THRESHOLD_EMBEDDINGS = 0.3   # Más bajo = más candidatos
THRESHOLD_FINAL = 0.5        # Mínimo score para match válido
NAME_WEIGHT = 0.7            # Peso del nombre (0-1)
ACRONYM_WEIGHT = 0.3         # Peso del acrónimo (0-1)
COSINE_WEIGHT = 0.50         # Peso de embeddings en score final
FUZZ_NAME_WEIGHT = 0.40      # Peso de texto nombre en score final
FUZZ_ACRONYM_WEIGHT = 0.10   # Peso de texto acrónimo en score final
```

### Ejemplos de ajuste:

**Más restrictivo (menos matches, más precisión):**
```python
THRESHOLD_FINAL = 0.7  # Solo matches con 70%+ score
```

**Más permisivo (más matches, menor precisión):**
```python
THRESHOLD_FINAL = 0.4  # Acepta matches con 40%+ score
```

**Priorizar acrónimos:**
```python
NAME_WEIGHT = 0.5
ACRONYM_WEIGHT = 0.5
# Y en score final:
FUZZ_ACRONYM_WEIGHT = 0.20  # Duplicar peso de acrónimo
FUZZ_NAME_WEIGHT = 0.30     # Reducir nombre
```

---

## 📈 Interpretación de Resultados

### Match Quality

- **excellent** (≥0.85): Match muy confiable, revisar solo casos excepcionales
- **good** (≥0.70): Match confiable, revisar algunos casos
- **fair** (≥0.50): Match aceptable, **revisar manualmente**
- **no_match**: No se encontró match arriba del threshold

### Scores Individuales

**COSINE_SIMILARITY** (similitud vectorial):
- > 0.90: Prácticamente idéntico semánticamente
- 0.70-0.90: Muy similar
- 0.50-0.70: Moderadamente similar
- < 0.50: Poco similar

**FUZZ_NAME_SCORE** (similitud de texto):
- 1.00: Texto idéntico
- > 0.80: Muy similar
- 0.50-0.80: Parcialmente similar
- < 0.50: Diferentes

**FINAL_SCORE** (combinación de ambos):
- El score que se usa para determinar el match
- Combina semántica + texto + acrónimo

---

## 🎯 Flujo del Proceso

```
Para cada fila del Excel:
  ↓
1. Leer partner_name y acronym
  ↓
2. Generar embeddings con Amazon Titan
  ↓
3. Buscar Top 5 candidatos en Supabase
   (usando similitud coseno de embeddings)
  ↓
4. Refinar con RapidFuzz (comparación de texto)
  ↓
5. Calcular score final combinado
  ↓
6. Si score ≥ THRESHOLD_FINAL → MATCH
   Si score < THRESHOLD_FINAL → NO MATCH
```

---

## 💡 Consejos

### 1. Revisar matches "fair"

Los matches con calidad "fair" (0.50-0.70) deben revisarse manualmente:

```python
# Filtrar en pandas después
import pandas as pd
df = pd.read_excel("clarisa_mapping_results.xlsx")
revisar = df[df['MATCH_QUALITY'] == 'fair']
revisar.to_excel("revision_manual.xlsx", index=False)
```

### 2. Verificar sin match

Instituciones sin match pueden necesitar:
- Búsqueda manual en CLARISA
- Ajustar threshold más bajo
- Verificar que existan en CLARISA

### 3. Procesar en batches

Si tienes muchas instituciones (>1000), procesa en batches:

```python
# En mapping_clarisa_comparison.py
df = pd.read_excel(excel_file)
batch = df.head(100)  # Primeras 100
batch.to_excel("batch_1.xlsx", index=False)

# Luego procesa batch_1.xlsx
```

---

## 🐛 Solución de Problemas

### Error: "La base de datos está vacía"

```bash
# Ejecutar primero
python populate_clarisa_db.py
```

### Error: "No se encuentra el archivo Excel"

Verifica la ruta del archivo en `mapping_clarisa_comparison.py` línea ~265.

### Muchos "no_match"

Intenta:
1. Bajar `THRESHOLD_FINAL` a 0.4 o 0.3
2. Verificar que los nombres en el Excel sean correctos
3. Revisar que la DB de CLARISA esté completa

### Matches incorrectos

Intenta:
1. Subir `THRESHOLD_FINAL` a 0.6 o 0.7
2. Ajustar pesos (más peso en acrónimos si son confiables)
3. Revisar normalización de texto

---

## 📚 Documentación Relacionada

- [README.md](README.md) - Documentación general del proyecto
- [QUICKSTART.md](QUICKSTART.md) - Guía de inicio rápido
- [docs/COMO_FUNCIONA_LA_BUSQUEDA.md](docs/COMO_FUNCIONA_LA_BUSQUEDA.md) - Explicación técnica de la búsqueda
- [search_example.py](search_example.py) - Ejemplos de uso de la API

---

## ✅ Ejemplo Completo

```bash
# 1. Preparar Excel (columnas: id, partner_name, acronym)
# 2. Asegurar que la DB esté poblada
python populate_clarisa_db.py  # Si no lo hiciste antes

# 3. Configurar archivo en mapping_clarisa_comparison.py
# excel_file = "mi_archivo.xlsx"

# 4. Ejecutar
python mapping_clarisa_comparison.py

# 5. Revisar resultados
# clarisa_mapping_results.xlsx
```

**Output esperado:**
```
🚀 PIPELINE DE MAPEO: CGSpace → CLARISA
✅ Base de datos lista: 10,237 instituciones en CLARISA
📊 Cargando archivo Excel: File To Dani (1).xlsx
✅ 500 filas cargadas

Buscando matches: 100%|███████████████| 500/500

📊 RESULTADOS
✅ Archivo guardado: clarisa_mapping_results.xlsx

📈 Estadísticas:
   Total procesado:     500
   ✅ Matches exitosos: 420 (84.0%)
   ❌ Sin match:        80 (16.0%)
   
🏆 Calidad de matches:
   Excelente (≥0.85): 350 (83.3%)
   Bueno (≥0.70):     50 (11.9%)
   Aceptable (≥0.50): 20 (4.8%)

✅ PROCESO COMPLETADO
```

---

¿Listo para procesar tus instituciones? 🚀
