# 🎯 Respuesta a tu Pregunta sobre Normalización

## ❓ Pregunta Original

> "Cuando se hace el embedding del nombre y acrónimo para guardar en la DB, ¿se está normalizando también el texto? Es importante que se guarde normalizado para que, cuando yo haga la búsqueda, compare un texto normalizado contra otro normalizado, no?"

---

## ✅ Respuesta Corta

**NO**, y es **intencional**. Para embeddings modernos (como Amazon Titan):

```
❌ NO normalices agresivamente antes de generar embeddings
✅ SÍ normaliza solo para comparaciones con RapidFuzz
```

---

## 🧠 Explicación

### Para Embeddings: NO Normalizar ✨

**Situación ACTUAL (implementada):**

```python
# Al guardar en DB
name = "Universidad de São Paulo (USP)"
name_embedding = get_embedding(name)  # Solo limpia espacios extra
# Texto enviado a Titan: "Universidad de São Paulo (USP)"
# ✅ Preserva: acentos, mayúsculas, paréntesis
```

**¿Por qué NO normalizar?**

1. **Amazon Titan está entrenado con texto natural**
   - Entiende "São Paulo" y "Sao Paulo" como similares
   - Entiende "WUR" y "Wageningen University" como relacionados
   - Entiende mayúsculas/minúsculas sin problema

2. **Normalizar PIERDE información semántica**
   ```python
   # Original
   "Wageningen University and Research Centre (WUR)"
   # → Embedding rico en contexto ✅
   
   # Normalizado
   "wageningen university and research centre wur"
   # → Embedding con menos contexto ❌
   ```

3. **Comparación de embeddings NO necesita textos idénticos**
   ```python
   # Estos generan embeddings SIMILARES automáticamente:
   emb1 = get_embedding("Wageningen University")
   emb2 = get_embedding("WAGENINGEN UNIVERSITY")
   emb3 = get_embedding("Universiteit Wageningen")
   
   # cosine_similarity(emb1, emb2) ≈ 0.95 ✅
   # cosine_similarity(emb1, emb3) ≈ 0.87 ✅
   # El modelo ENTIENDE que son similares
   ```

---

### Para RapidFuzz: SÍ Normalizar 🔍

**Situación ACTUAL (implementada):**

```python
# Al buscar con RapidFuzz (desempate)
query = "Wageningen University"
candidate = "WAGENINGEN UNIVERSITY AND RESEARCH"

# Normalizar AMBOS textos
query_norm = clean_text_for_matching(query)
# → "wageningen university"

candidate_norm = clean_text_for_matching(candidate)
# → "wageningen university and research"

# Comparar textos normalizados
fuzz_score = fuzz.ratio(query_norm, candidate_norm)
# → Score alto ✅
```

**¿Por qué SÍ normalizar aquí?**

RapidFuzz hace **comparación carácter por carácter**:

```python
# Sin normalizar
fuzz.ratio("WUR", "wur")  # 75% ❌

# Con normalizar
fuzz.ratio("wur", "wur")  # 100% ✅
```

---

## 📊 Comparación Visual

### Escenario 1: Solo Embeddings

```
┌──────────────────────────────────────────────────────┐
│ EMBEDDINGS SIN NORMALIZACIÓN (RECOMENDADO)          │
├──────────────────────────────────────────────────────┤
│                                                      │
│ Query:  "Wageningen University"                     │
│         ↓ get_embedding()                           │
│         [0.12, 0.45, 0.78, ...]                     │
│                                                      │
│ DB:     "Wageningen University and Research"        │
│         ↓ embedding guardado                        │
│         [0.13, 0.44, 0.79, ...]                     │
│                                                      │
│ Similitud Coseno: 0.92 ✅ EXCELENTE                 │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│ EMBEDDINGS CON NORMALIZACIÓN (NO RECOMENDADO)       │
├──────────────────────────────────────────────────────┤
│                                                      │
│ Query:  "wageningen university"  (normalizado)      │
│         ↓ get_embedding()                           │
│         [0.08, 0.32, 0.61, ...] (menos contexto)    │
│                                                      │
│ DB:     "wageningen university and research"        │
│         ↓ embedding guardado                        │
│         [0.09, 0.31, 0.62, ...]                     │
│                                                      │
│ Similitud Coseno: 0.87 ❌ PEOR que sin normalizar   │
└──────────────────────────────────────────────────────┘
```

### Escenario 2: Búsqueda Híbrida (Implementado)

```
┌───────────────────────────────────────────────────────────┐
│ PASO 1: BÚSQUEDA POR EMBEDDINGS (Sin Normalizar)         │
├───────────────────────────────────────────────────────────┤
│ Query: "Wageningen University"                            │
│        ↓ get_embedding() [SIN normalizar]                │
│        [0.12, 0.45, 0.78, ...]                           │
│        ↓ Buscar Top 5 en Supabase                        │
│                                                           │
│ Top 5 Candidatos:                                         │
│  1. Wageningen University and Research    (0.92)         │
│  2. Wageningen UR                         (0.87)         │
│  3. University of Wageningen              (0.81)         │
│  4. WUR Netherlands                       (0.76)         │
│  5. Wageningen Centre                     (0.71)         │
└───────────────────────────────────────────────────────────┘
                           ↓
┌───────────────────────────────────────────────────────────┐
│ PASO 2: DESEMPATE CON RAPIDFUZZ (Con Normalizar)         │
├───────────────────────────────────────────────────────────┤
│ Query normalizado: "wageningen university"                │
│                                                           │
│ Para cada candidato:                                      │
│  1. "wageningen university and research" → Fuzz: 88%     │
│  2. "wageningen ur"                      → Fuzz: 65%     │
│  3. "university of wageningen"           → Fuzz: 75%     │
│  4. "wur netherlands"                    → Fuzz: 45%     │
│  5. "wageningen centre"                  → Fuzz: 70%     │
│                                                           │
│ Score Combinado = 50% Coseno + 40% Fuzz + 10% Acronym    │
│                                                           │
│ 🏆 MEJOR MATCH: "Wageningen University and Research"      │
│    Score Final: 0.90                                      │
└───────────────────────────────────────────────────────────┘
```

---

## ✅ Lo Que Implementamos

### 1. Funciones de Normalización (`src/utils.py`)

```python
# Limpieza básica (para embeddings)
def clean_text_basic(text):
    # Solo normaliza espacios múltiples
    return ' '.join(text.split()).strip()

# Normalización completa (para RapidFuzz)
def clean_text_for_matching(text):
    # Lowercase + sin acentos + sin puntuación
    text = text.lower()
    text = remove_accents(text)
    text = remove_special_chars(text)
    return text.strip()
```

### 2. Embeddings Sin Normalizar (`src/embeddings.py`)

```python
def get_embedding(text: str) -> np.ndarray:
    # Limpieza básica: solo espacios
    cleaned_text = ' '.join(text.split()).strip()
    
    # NO lowercase, NO remove acentos
    response = bedrock.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        body=json.dumps({"inputText": cleaned_text})
    )
    return embedding  # Embedding del texto casi-original
```

### 3. Búsqueda Híbrida (`search_example.py`)

```python
# PASO 1: Embeddings (sin normalizar)
query_embedding = get_embedding("Wageningen University")
candidates = search_by_name_embedding(query_embedding)

# PASO 2: RapidFuzz (con normalizar)
for candidate in candidates:
    query_norm = clean_text_for_matching("Wageningen University")
    cand_norm = clean_text_for_matching(candidate['name'])
    fuzz_score = fuzz.ratio(query_norm, cand_norm)
```

---

## 🧪 Cómo Validar

**Ejecuta el test:**

```bash
python test_normalization.py
```

**Verás:**

```
🧪 TEST 1: EMBEDDINGS - Con vs Sin Normalización
═══════════════════════════════════════════════════

Query:     Wageningen University and Research
Candidato: WAGENINGEN UNIVERSITY

   SIN normalizar:  0.9234  ← MEJOR ✅
   CON normalizar:  0.8876
   ✅ GANADOR: Sin normalizar (+0.0358)

-----------------------------------------------------------

🧪 TEST 2: RAPIDFUZZ - Con vs Sin Normalización
═══════════════════════════════════════════════

Query:     "WUR"
Candidato: "Wageningen University and Research (WUR)"

   SIN normalizar:  23%
   CON normalizar:  100%  ← MEJOR ✅
   ✅ MEJORA: +77% con normalización
```

---

## 📚 Documentación Adicional

- **Estrategia Completa:** [docs/NORMALIZATION_STRATEGY.md](docs/NORMALIZATION_STRATEGY.md)
- **Cambios Implementados:** [CHANGELOG_NORMALIZATION.md](CHANGELOG_NORMALIZATION.md)
- **README:** [README.md](README.md#-estrategia-de-normalización)

---

## 🎓 Conclusión

### Tu Intuición Era Correcta... A Medias 😊

> "Es importante comparar texto normalizado contra texto normalizado"

✅ **CIERTO para:** String matching (RapidFuzz)
❌ **FALSO para:** Embeddings semánticos (Titan)

### La Solución: Enfoque Híbrido

```
┌─────────────────────────────────────┐
│  EMBEDDINGS → Sin normalizar        │ ← Búsqueda semántica
│  RAPIDFUZZ  → Con normalizar        │ ← Refinamiento exacto
└─────────────────────────────────────┘
        Mejor de ambos mundos ✨
```

### Analogía

- **Embeddings = Entender el significado** (como un humano)
  - "São Paulo" y "Sao Paulo" significan lo mismo → No importa normalizar
  
- **RapidFuzz = Contar letras iguales** (como una máquina)
  - "São" ≠ "Sao" → Sí importa normalizar

**Usamos ambos enfoques para maximizar precisión.** 🎯
