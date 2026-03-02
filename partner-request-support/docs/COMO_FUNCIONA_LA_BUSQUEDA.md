# 🔍 Cómo Funciona la Búsqueda - Explicación Detallada

## 📊 Datos en la Base de Datos

Cada institución en Supabase tiene **DOS embeddings separados**:

```
Institución en DB: "Wageningen University and Research Centre"
├── name: "Wageningen University and Research Centre"
├── name_embedding: [0.12, 0.45, 0.78, ..., 0.33]  ← 1024 números (embedding del NOMBRE)
├── acronym: "WUR"
└── acronym_embedding: [0.88, 0.23, 0.91, ..., 0.15]  ← 1024 números (embedding del ACRÓNIMO)
```

**Estos embeddings se generan UNA SOLA VEZ** cuando ejecutas `populate_clarisa_db.py`:

```python
# Al poblar la DB
name_embedding = get_embedding("Wageningen University and Research Centre")
# → [0.12, 0.45, 0.78, ..., 0.33]  (1024 números)

acronym_embedding = get_embedding("WUR")
# → [0.88, 0.23, 0.91, ..., 0.15]  (1024 números)
```

---

## 🔎 Proceso de Búsqueda - 3 Pasos

### PASO 1: Generar Embeddings del Query 🧠

Cuando buscas, **primero generas embeddings** de lo que quieres buscar:

```python
# Tu búsqueda
partner_name = "Wageningen University"
acronym = "WUR"

# Generar embeddings del QUERY
name_query_embedding = get_embedding("Wageningen University")
# → [0.11, 0.44, 0.79, ..., 0.32]  (1024 números)

acronym_query_embedding = get_embedding("WUR")
# → [0.89, 0.22, 0.90, ..., 0.14]  (1024 números)
```

---

### PASO 2: Búsqueda Vectorial (Top 5) 🎯

#### Caso A: Solo buscas por NOMBRE

```python
candidates = search_by_name_embedding(
    query_embedding=name_query_embedding,  # Tu búsqueda
    threshold=0.4,
    limit=5
)
```

**¿Qué compara?**

```
Tu Query Embedding (Nombre)    vs    DB name_embedding de CADA institución
[0.11, 0.44, 0.79, ...]       <=>    [0.12, 0.45, 0.78, ...]  (Wageningen U...)
                              <=>    [0.05, 0.33, 0.62, ...]  (MIT)
                              <=>    [0.09, 0.41, 0.75, ...]  (Cambridge)
                              <=>    ... (todas las instituciones)
```

**Cálculo de similitud:**
```sql
-- En Supabase (PostgreSQL)
similarity = 1 - (name_embedding <=> query_embedding)
-- <=> es el operador de distancia coseno en pgvector
-- 1 - distancia = similitud (0.0 = nada similar, 1.0 = idéntico)
```

**Resultado:** Top 5 con mayor similitud de NOMBRE

```
Top 5 Candidatos (por similitud de nombre):
1. Wageningen University and Research Centre    0.92
2. Wageningen UR                                 0.87
3. University of Wageningen                      0.81
4. WUR Netherlands                               0.76
5. Wageningen Centre for Development            0.71
```

---

#### Caso B: Buscas por NOMBRE + ACRÓNIMO (combinado)

```python
candidates = search_combined(
    name_embedding=name_query_embedding,      # Tu búsqueda de nombre
    acronym_embedding=acronym_query_embedding, # Tu búsqueda de acrónimo
    name_weight=0.7,      # 70% peso al nombre
    acronym_weight=0.3,   # 30% peso al acrónimo
    threshold=0.4,
    limit=5
)
```

**¿Qué compara?**

```
PARA CADA INSTITUCIÓN EN LA DB:

1. Compara tu NOMBRE con su NOMBRE
   name_similarity = 1 - (name_query_embedding <=> ci.name_embedding)

2. Compara tu ACRÓNIMO con su ACRÓNIMO
   acronym_similarity = 1 - (acronym_query_embedding <=> ci.acronym_embedding)

3. Combina ambos scores con pesos
   combined_similarity = (name_similarity × 0.7) + (acronym_similarity × 0.3)
```

**Ejemplo con una institución:**

```
Institución: "Wageningen University and Research Centre (WUR)"

┌─────────────────────────────────────────────────────────┐
│ COMPARACIÓN DE EMBEDDINGS                               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 1. Similitud de NOMBRE:                                 │
│    Tu query:    "Wageningen University"                 │
│    Su nombre:   "Wageningen University and Research..." │
│    Embedding:   [0.11, ...] <=> [0.12, ...]           │
│    Similitud:   0.92  ✅                                │
│                                                         │
│ 2. Similitud de ACRÓNIMO:                               │
│    Tu query:    "WUR"                                   │
│    Su acrónimo: "WUR"                                   │
│    Embedding:   [0.89, ...] <=> [0.88, ...]           │
│    Similitud:   0.98  ✅                                │
│                                                         │
│ 3. Score Combinado:                                     │
│    (0.92 × 0.7) + (0.98 × 0.3) = 0.938  🏆            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Resultado:** Top 5 con mayor similitud COMBINADA

```
Top 5 Candidatos (nombre + acrónimo combinado):
                                          Nombre  Acronym  Combined
1. Wageningen University and Research...  0.92    0.98     0.938  🏆
2. WUR Netherlands                        0.76    0.98     0.826
3. Wageningen UR                          0.87    0.75     0.840
4. University of Wageningen               0.81    0.60     0.747
5. World Resources Institute              0.45    0.15     0.360
```

---

### PASO 3: Desempate con RapidFuzz 🎲

Ahora tienes los **Top 5 candidatos**. Para decidir el mejor, usas RapidFuzz:

```python
for candidate in top_5_candidates:
    # 1. Ya tienes la similitud coseno (del paso anterior)
    cosine_sim = candidate['combined_similarity']  # ej: 0.938
    
    # 2. Comparar NOMBRES con RapidFuzz (texto normalizado)
    query_norm = clean_text_for_matching("Wageningen University")
    # → "wageningen university"
    
    candidate_norm = clean_text_for_matching(candidate['name'])
    # → "wageningen university and research centre wur"
    
    fuzz_name = fuzz.ratio(query_norm, candidate_norm) / 100
    # → 0.88 (88% de caracteres coinciden)
    
    # 3. Comparar ACRÓNIMOS con RapidFuzz (si hay)
    if acronym and candidate['acronym']:
        query_acr_norm = clean_text_for_matching("WUR")
        # → "wur"
        
        cand_acr_norm = clean_text_for_matching("WUR")
        # → "wur"
        
        fuzz_acronym = fuzz.ratio(query_acr_norm, cand_acr_norm) / 100
        # → 1.00 (100% idénticos)
    
    # 4. Score final combinado
    final_score = (
        0.50 × cosine_sim +      # 50% similitud de embeddings
        0.40 × fuzz_name +       # 40% similitud de texto (nombre)
        0.10 × fuzz_acronym      # 10% similitud de texto (acrónimo)
    )
    # = (0.50 × 0.938) + (0.40 × 0.88) + (0.10 × 1.00)
    # = 0.469 + 0.352 + 0.100
    # = 0.921 ✨
```

**El candidato con el SCORE FINAL más alto es tu mejor match.** 🏆

---

## 📊 Resumen Visual Completo

```
┌──────────────────────────────────────────────────────────────────┐
│                    FLUJO COMPLETO DE BÚSQUEDA                    │
└──────────────────────────────────────────────────────────────────┘

TU BÚSQUEDA:
  partner_name = "Wageningen University"
  acronym = "WUR"

↓

PASO 1: GENERAR EMBEDDINGS DEL QUERY
  name_embedding = get_embedding("Wageningen University")
  → [0.11, 0.44, 0.79, ..., 0.32]  (1024 números)
  
  acronym_embedding = get_embedding("WUR")
  → [0.89, 0.22, 0.90, ..., 0.14]  (1024 números)

↓

PASO 2: BÚSQUEDA VECTORIAL EN SUPABASE
  Función RPC: search_combined(
    name_embedding, 
    acronym_embedding,
    name_weight=0.7,
    acronym_weight=0.3
  )

  Para CADA institución en la DB:
    ┌─────────────────────────────────────────────────┐
    │ Institución: "Wageningen University and..."     │
    ├─────────────────────────────────────────────────┤
    │ Compara:                                        │
    │   [0.11, ...] <=> DB.name_embedding             │
    │   Similitud nombre: 0.92                        │
    │                                                 │
    │   [0.89, ...] <=> DB.acronym_embedding          │
    │   Similitud acrónimo: 0.98                      │
    │                                                 │
    │   Combined: (0.92×0.7) + (0.98×0.3) = 0.938    │
    └─────────────────────────────────────────────────┘
  
  Ordena por combined_similarity → Top 5

↓

PASO 3: DESEMPATE CON RAPIDFUZZ
  Para cada uno de los Top 5:
    
    Cosine (ya calculado):  0.938
    
    Fuzz Nombre:
      "wageningen university" vs "wageningen university and research..."
      → 0.88
    
    Fuzz Acrónimo:
      "wur" vs "wur"
      → 1.00
    
    SCORE FINAL:
      (0.50 × 0.938) + (0.40 × 0.88) + (0.10 × 1.00) = 0.921

↓

MEJOR MATCH 🏆
  Institución: "Wageningen University and Research Centre"
  Score Final: 0.921
```

---

## 🎯 Qué Compara con Qué - Tabla Resumen

| Etapa | Tu Input | Se Compara Con | Tipo de Comparación |
|-------|----------|----------------|---------------------|
| **Embeddings - Nombre** | Embedding de "Wageningen University" | `name_embedding` de cada institución en DB | Similitud coseno de vectores |
| **Embeddings - Acrónimo** | Embedding de "WUR" | `acronym_embedding` de cada institución en DB | Similitud coseno de vectores |
| **RapidFuzz - Nombre** | "wageningen university" (normalizado) | "wageningen university and..." (normalizado) | Similitud de caracteres (%) |
| **RapidFuzz - Acrónimo** | "wur" (normalizado) | "wur" (normalizado) | Similitud de caracteres (%) |

---

## 🔧 Cómo Juegan el Nombre y el Acrónimo

### 1. En la Base de Datos (al guardar)

```python
# Institución de CLARISA
{
  "code": 1,
  "name": "Wageningen University and Research Centre",
  "acronym": "WUR"
}

# Se generan DOS embeddings separados
name_embedding = get_embedding("Wageningen University and Research Centre")
acronym_embedding = get_embedding("WUR")

# Se guardan en DB
{
  "clarisa_id": 1,
  "name": "Wageningen University and Research Centre",
  "name_embedding": [1024 números],  ← Embedding del NOMBRE completo
  "acronym": "WUR",
  "acronym_embedding": [1024 números]  ← Embedding del ACRÓNIMO solito
}
```

### 2. En la Búsqueda (al consultar)

#### Opción A: Solo buscas por nombre

```python
search_by_name_embedding("Wageningen University")
```

**Compara:**
- Tu embedding de "Wageningen University"
- vs `name_embedding` de todas las instituciones
- ✅ Ignora completamente los acrónimos

#### Opción B: Solo buscas por acrónimo

```python
search_by_acronym_embedding("WUR")
```

**Compara:**
- Tu embedding de "WUR"
- vs `acronym_embedding` de todas las instituciones
- ✅ Ignora completamente los nombres

#### Opción C: Búsqueda combinada (RECOMENDADO)

```python
search_combined("Wageningen University", "WUR", name_weight=0.7, acronym_weight=0.3)
```

**Compara:**
- Tu embedding de "Wageningen University" vs `name_embedding` → Score A
- Tu embedding de "WUR" vs `acronym_embedding` → Score B
- Score Final = (A × 0.7) + (B × 0.3)

**Ventaja:** Encuentra matches incluso si el nombre es diferente pero el acrónimo coincide, o viceversa.

---

## 💡 Ejemplos Prácticos

### Ejemplo 1: Nombre similar, acrónimo diferente

```
Query: "World Resources Institute" + "WRI"

Candidato 1: "World Resources Institute" (WRI)
  - Nombre similar: 1.00 ✅
  - Acrónimo similar: 1.00 ✅
  - Combined: (1.00×0.7) + (1.00×0.3) = 1.00 🏆

Candidato 2: "World Research Institute" (WRE)
  - Nombre similar: 0.95 ✅
  - Acrónimo similar: 0.65 ⚠️
  - Combined: (0.95×0.7) + (0.65×0.3) = 0.86

→ Gana Candidato 1 (match perfecto)
```

### Ejemplo 2: Nombre diferente, acrónimo igual

```
Query: "Massachusetts Institute of Technology" + "MIT"

Candidato 1: "MIT" (MIT)
  - Nombre similar: 0.40 ⚠️ (nombre muy corto vs largo)
  - Acrónimo similar: 1.00 ✅
  - Combined: (0.40×0.7) + (1.00×0.3) = 0.58

Candidato 2: "Massachusetts Institute" (MIT)
  - Nombre similar: 0.92 ✅
  - Acrónimo similar: 1.00 ✅
  - Combined: (0.92×0.7) + (1.00×0.3) = 0.94 🏆

→ Gana Candidato 2 (nombre + acrónimo mejores)
```

### Ejemplo 3: Solo tienes el nombre

```
Query: "Wageningen University" (sin acrónimo)

Se usa: search_by_name_embedding()

Candidato 1: "Wageningen University and Research Centre"
  - Nombre similar: 0.92 ✅
  
Candidato 2: "University of Wageningen"
  - Nombre similar: 0.81

→ Gana Candidato 1
```

---

## 🎛️ Ajustes de Pesos

Puedes cambiar cómo influye cada factor:

```python
# Búsqueda vectorial (Supabase)
search_combined(
    name_weight=0.7,      # ← Cambiar: más peso al nombre
    acronym_weight=0.3    # ← Cambiar: menos peso al acrónimo
)

# Desempate (RapidFuzz)
final_score = (
    0.50 * cosine_sim +   # ← Cambiar: peso de embeddings
    0.40 * fuzz_name +    # ← Cambiar: peso de texto (nombre)
    0.10 * fuzz_acronym   # ← Cambiar: peso de texto (acrónimo)
)
```

### Ejemplo de ajuste:

Si los acrónimos son muy confiables en tus datos:

```python
# Dar más peso al acrónimo
search_combined(name_weight=0.5, acronym_weight=0.5)

final_score = (
    0.40 * cosine_sim +    # Menos peso a embeddings
    0.30 * fuzz_name +     # Menos peso al nombre
    0.30 * fuzz_acronym    # Más peso al acrónimo
)
```

---

## ❓ Preguntas Frecuentes

### ¿Por qué separar nombre y acrónimo?

**Ventajas:**
1. Puedes buscar solo por uno u otro
2. Puedes ajustar pesos independientemente
3. Algunas instituciones tienen nombres similares pero acrónimos únicos
4. Permite búsquedas más flexibles

**Ejemplo:**
- "CGIAR" (acrónimo) muy diferente de "Consultative Group on International Agricultural Research" (nombre)
- Si buscas "CGIAR", encontrarlo por `acronym_embedding` es más efectivo

### ¿Qué pasa si una institución no tiene acrónimo?

```python
# En la DB
{
  "name": "Universidad de Buenos Aires",
  "acronym": null,
  "name_embedding": [1024 números],
  "acronym_embedding": null  ← No se generó
}

# En búsqueda combinada
acronym_similarity = COALESCE(..., 0)  # = 0 si es null
combined = (0.85×0.7) + (0×0.3) = 0.595
# Solo cuenta el nombre, acrónimo = 0
```

### ¿Los embeddings se regeneran en cada búsqueda?

**NO** ❌

- Los embeddings de las **instituciones en DB**: Se generan UNA VEZ (al poblar)
- Los embeddings del **query**: Se generan cada vez que buscas

```python
# Una sola vez (al poblar)
populate_clarisa_db.py → genera embeddings de 10,000+ instituciones

# Cada búsqueda (rápido)
search_example.py → solo genera embedding del query (2 vectores)
```

---

¿Quedó claro? 🎯
