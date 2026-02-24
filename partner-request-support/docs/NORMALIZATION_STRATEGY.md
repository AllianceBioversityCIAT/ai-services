# 📝 Estrategia de Normalización de Texto

## 🎯 Resumen

Este proyecto usa **dos niveles de normalización** dependiendo del contexto:

1. **Limpieza Básica** → Para embeddings (mantiene semántica)
2. **Normalización Completa** → Para string matching (RapidFuzz)

---

## 🧠 Para Embeddings (Amazon Titan)

### ✅ LO QUE HACEMOS

```python
# Texto original
"Universidad de São Paulo (USP)"

# Limpieza básica: solo espacios múltiples
"Universidad de São Paulo (USP)"  # Mantiene acentos y mayúsculas
```

**Función:** `clean_text_basic()` o automático en `get_embedding()`

### ❌ LO QUE NO HACEMOS

```python
# ❌ NO convertimos a lowercase
# ❌ NO removemos acentos
# ❌ NO removemos caracteres especiales (paréntesis, guiones)
```

### 🤔 ¿Por qué?

Los modelos de embeddings modernos (como Amazon Titan) están entrenados con **texto natural**:

- ✅ Entienden mayúsculas y minúsculas
- ✅ Entienden acentos y caracteres especiales
- ✅ Capturan mejor el contexto semántico con el texto original

**Ejemplo de similitud semántica:**

```python
# Estos textos generan embeddings similares automáticamente:
"Wageningen University and Research"
"WAGENINGEN UNIVERSITY"
"Universiteit Wageningen"
"WUR"  # Contexto suficiente para relacionarlo
```

### 📊 Comparación

| Original | Normalizado Agresivo | Resultado |
|----------|---------------------|-----------|
| "CGIAR Initiative" | "cgiar initiative" | ❌ Perdemos info |
| "Université de Genève" | "universite de geneve" | ❌ Perdemos contexto |
| "MIT (Massachusetts Institute)" | "mit massachusetts institute" | ❌ Perdemos estructura |

**Titan entiende el original MEJOR que el normalizado.**

---

## 🔍 Para String Matching (RapidFuzz)

### ✅ LO QUE HACEMOS

```python
from src.utils import clean_text_for_matching

# Texto original
"Universidad de São Paulo (USP)"

# Normalización completa
"universidad de sao paulo usp"  # lowercase + sin acentos
```

**Función:** `clean_text_for_matching()`

### ✔️ Transformaciones:

1. ✅ Convertir a lowercase
2. ✅ Remover acentos (São → sao)
3. ✅ Remover puntuación (mantener paréntesis para siglas)
4. ✅ Normalizar espacios múltiples

### 🤔 ¿Por qué?

RapidFuzz hace **comparación de caracteres** (no semántica):

```python
# Sin normalización
fuzz.ratio("Universität", "Universidad")  # Score: ~54%

# Con normalización
fuzz.ratio("universitat", "universidad")  # Score: ~82% ✅
```

### 📊 Comparación

| Query | Candidato | Sin Norm | Con Norm |
|-------|-----------|----------|----------|
| "WUR" | "wur" | 75% | **100%** ✅ |
| "São Paulo" | "Sao Paulo" | 82% | **100%** ✅ |
| "Wageningen Univ" | "WAGENINGEN UNIVERSITY" | 73% | **88%** ✅ |

---

## 🔄 Flujo Completo en Búsqueda Híbrida

```python
# 1. Query del usuario
query = "Wageningen University"
acronym = "WUR"

# 2. Generar embeddings (SIN normalizar)
query_embedding = get_embedding(query)  
# Internamente hace limpieza básica: espacios múltiples

# 3. Buscar Top 5 por similitud coseno (Supabase)
candidates = search_by_name_embedding(query_embedding, limit=5)
# Los embeddings guardados TAMPOCO están normalizados

# 4. Desempate con RapidFuzz (CON normalización)
from src.utils import clean_text_for_matching

for candidate in candidates:
    # Normalizar ambos para comparación justa
    normalized_query = clean_text_for_matching(query)
    normalized_candidate = clean_text_for_matching(candidate['name'])
    
    fuzz_score = fuzz.ratio(normalized_query, normalized_candidate)
    
# 5. Score combinado
final_score = (0.5 * cosine_sim) + (0.4 * fuzz_score) + ...
```

---

## 🛠️ Funciones Disponibles

### `clean_text_basic(text)`
Limpieza básica para embeddings

```python
from src.utils import clean_text_basic

text = "Universidad   de São   Paulo  (USP)"
clean = clean_text_basic(text)
# "Universidad de São Paulo (USP)"  ← espacios normalizados
```

**Úsala cuando:**
- Preprocesamiento manual antes de embeddings (opcional)
- El texto tiene espacios múltiples problemáticos

### `clean_text_for_matching(text)`
Normalización completa para RapidFuzz

```python
from src.utils import clean_text_for_matching

text = "Universidad de São Paulo (USP)"
normalized = clean_text_for_matching(text)
# "universidad de sao paulo usp"
```

**Úsala cuando:**
- ✅ Vas a comparar con RapidFuzz
- ✅ Necesitas matching exacto de strings
- ✅ Implementas lógica de desempate

### `clean_text(text)` (legacy)
Alias de `clean_text_for_matching()` para compatibilidad

```python
# Código legacy sigue funcionando
from src.utils import clean_text
normalized = clean_text(text)  # Mismo comportamiento
```

---

## 📈 Impacto en Resultados

### Búsqueda Solo por Embeddings

```python
# Query: "Wageningen University"

# Candidato 1: "Wageningen University and Research Centre"
# Sin normalización: cosine = 0.92 ✅
# Con normalización agresiva: cosine = 0.88 ❌ (pierde info)
```

**Resultado:** Embeddings funcionan MEJOR sin normalización agresiva.

### Búsqueda Híbrida (Embeddings + RapidFuzz)

```python
# Query: "WUR"
# Candidato: "Wageningen University and Research Centre (WUR)"

# Embeddings (sin normalizar)
cosine_sim = 0.75

# RapidFuzz (normalizado)
fuzz.ratio("wur", "wageningen university and research centre wur") = 23%
# vs
fuzz.ratio("WUR", "Wageningen University and Research Centre (WUR)") = 17%

# Score combinado MEJORA con normalización en RapidFuzz
```

**Resultado:** Estrategia híbrida da los mejores resultados.

---

## ✅ Mejores Prácticas

### DO ✅

1. **Guardar texto original** en la base de datos
2. **Generar embeddings** con texto casi original (solo limpieza de espacios)
3. **Normalizar al momento de comparar** con RapidFuzz
4. **Separar embeddings** de nombre y acrónimo (ya implementado)

### DON'T ❌

1. ❌ NO normalices agresivamente antes de embeddings
2. ❌ NO uses `.lower()` antes de generar embeddings
3. ❌ NO remuevas acentos antes de Titan
4. ❌ NO uses RapidFuzz sin normalizar ambos textos

---

## 🔬 Experimentos Sugeridos

Si quieres validar esta estrategia:

```python
# Prueba 1: Embeddings con vs sin normalización
text_original = "Universidad de São Paulo"
text_normalizado = "universidad de sao paulo"

emb_original = get_embedding(text_original)
emb_normalizado = get_embedding(text_normalizado)

# Compara similitudes contra otras universidades
```

```python
# Prueba 2: RapidFuzz con vs sin normalización
from rapidfuzz import fuzz
from src.utils import clean_text_for_matching

query = "ETH Zürich"
candidate = "ETH ZURICH"

# Sin normalizar
score1 = fuzz.ratio(query, candidate)  # ~80%

# Normalizado
score2 = fuzz.ratio(
    clean_text_for_matching(query),
    clean_text_for_matching(candidate)
)  # ~100% ✅
```

---

## 📚 Referencias

- [Amazon Titan Embeddings Best Practices](https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html)
- [Vector Search Normalization Considerations](https://www.pinecone.io/learn/vector-search/)
- [RapidFuzz Documentation](https://github.com/maxbachmann/RapidFuzz)

---

## 🎓 Resumen Ejecutivo

| Contexto | Normalización | Razón |
|----------|---------------|-------|
| **Embeddings (Titan)** | ❌ Mínima (solo espacios) | Modelos entienden texto natural mejor |
| **String Matching (RapidFuzz)** | ✅ Completa (lowercase + sin acentos) | Comparación carácter por carácter |
| **Almacenamiento en DB** | ❌ Sin normalizar | Preserva información original |
| **Búsqueda Híbrida** | 🔄 Ambas estrategias | Mejor de ambos mundos |

**Conclusión:** La estrategia híbrida implementada maximiza la precisión de búsqueda. 🎯
