# 🔍 How the Search Works - Detailed Explanation

## 📊 Data in the Database

Each institution in Supabase has **TWO separate embeddings**:

```
Institution in DB: "Wageningen University and Research Centre"
├── name: "Wageningen University and Research Centre"
├── name_embedding: [0.12, 0.45, 0.78, ..., 0.33]  ← 1024 numbers (NAME embedding)
├── acronym: "WUR"
└── acronym_embedding: [0.88, 0.23, 0.91, ..., 0.15]  ← 1024 numbers (ACRONYM embedding)
```

**These embeddings are generated ONCE** when you run `populate_clarisa_db.py`:

```python
# When populating the DB
name_embedding = get_embedding("Wageningen University and Research Centre")
# → [0.12, 0.45, 0.78, ..., 0.33]  (1024 numbers)

acronym_embedding = get_embedding("WUR")
# → [0.88, 0.23, 0.91, ..., 0.15]  (1024 numbers)
```

---

## 🔎 Search Process - 3 Steps

### STEP 1: Generate Query Embeddings 🧠

When you search, **first you generate embeddings** of what you want to search for:

```python
# Your search
partner_name = "Wageningen University"
acronym = "WUR"

# Generate QUERY embeddings
name_query_embedding = get_embedding("Wageningen University")
# → [0.11, 0.44, 0.79, ..., 0.32]  (1024 numbers)

acronym_query_embedding = get_embedding("WUR")
# → [0.89, 0.22, 0.90, ..., 0.14]  (1024 numbers)
```

---

### STEP 2: Vector Search (Top 5) 🎯

#### Case A: Search by NAME only

```python
candidates = search_by_name_embedding(
    query_embedding=name_query_embedding,  # Your search
    threshold=0.4,
    limit=5
)
```

**What does it compare?**

```
Your Query Embedding (Name)    vs    DB name_embedding of EACH institution
[0.11, 0.44, 0.79, ...]       <=>    [0.12, 0.45, 0.78, ...]  (Wageningen U...)
                              <=>    [0.05, 0.33, 0.62, ...]  (MIT)
                              <=>    [0.09, 0.41, 0.75, ...]  (Cambridge)
                              <=>    ... (all institutions)
```

**Similarity calculation:**
```sql
-- In Supabase (PostgreSQL)
similarity = 1 - (name_embedding <=> query_embedding)
-- <=> is the cosine distance operator in pgvector
-- 1 - distance = similarity (0.0 = not similar, 1.0 = identical)
```

**Result:** Top 5 with highest NAME similarity

```
Top 5 Candidates (by name similarity):
1. Wageningen University and Research Centre    0.92
2. Wageningen UR                                 0.87
3. University of Wageningen                      0.81
4. WUR Netherlands                               0.76
5. Wageningen Centre for Development            0.71
```

---

#### Case B: Search by NAME + ACRONYM (combined)

```python
candidates = search_combined(
    name_embedding=name_query_embedding,      # Your name search
    acronym_embedding=acronym_query_embedding, # Your acronym search
    name_weight=0.7,      # 70% weight on name
    acronym_weight=0.3,   # 30% weight on acronym
    threshold=0.4,
    limit=5
)
```

**What does it compare?**

```
FOR EACH INSTITUTION IN THE DB:

1. Compare your NAME with its NAME
   name_similarity = 1 - (name_query_embedding <=> ci.name_embedding)

2. Compare your ACRONYM with its ACRONYM
   acronym_similarity = 1 - (acronym_query_embedding <=> ci.acronym_embedding)

3. Combine both scores with weights
   combined_similarity = (name_similarity × 0.7) + (acronym_similarity × 0.3)
```

**Example with one institution:**

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
    # 1. You already have the cosine similarity (from previous step)
    cosine_sim = candidate['combined_similarity']  # e.g.: 0.938
    
    # 2. Compare NAMES with RapidFuzz (normalized text)
    query_norm = clean_text_for_matching("Wageningen University")
    # → "wageningen university"
    
    candidate_norm = clean_text_for_matching(candidate['name'])
    # → "wageningen university and research centre wur"
    
    fuzz_name = fuzz.ratio(query_norm, candidate_norm) / 100
    # → 0.88 (88% of characters match)
    
    # 3. Compare ACRONYMS with RapidFuzz (if available)
    if acronym and candidate['acronym']:
        query_acr_norm = clean_text_for_matching("WUR")
        # → "wur"
        
        cand_acr_norm = clean_text_for_matching("WUR")
        # → "wur"
        
        fuzz_acronym = fuzz.ratio(query_acr_norm, cand_acr_norm) / 100
        # → 1.00 (100% identical)
    
    # 4. Final combined score
    final_score = (
        0.50 × cosine_sim +      # 50% embeddings similarity
        0.40 × fuzz_name +       # 40% text similarity (name)
        0.10 × fuzz_acronym      # 10% text similarity (acronym)
    )
    # = (0.50 × 0.938) + (0.40 × 0.88) + (0.10 × 1.00)
    # = 0.469 + 0.352 + 0.100
    # = 0.921 ✨
```

**The candidate with the highest FINAL SCORE is your best match.** 🏆

---

## 📊 Complete Visual Summary

```
┌──────────────────────────────────────────────────────────────────┐
│                    COMPLETE SEARCH FLOW                    │
└──────────────────────────────────────────────────────────────────┘

YOUR SEARCH:
  partner_name = "Wageningen University"
  acronym = "WUR"

↓

STEP 1: GENERATE QUERY EMBEDDINGS
  name_embedding = get_embedding("Wageningen University")
  → [0.11, 0.44, 0.79, ..., 0.32]  (1024 numbers)
  
  acronym_embedding = get_embedding("WUR")
  → [0.89, 0.22, 0.90, ..., 0.14]  (1024 numbers)

↓

STEP 2: VECTOR SEARCH IN SUPABASE
  RPC Function: search_combined(
    name_embedding, 
    acronym_embedding,
    name_weight=0.7,
    acronym_weight=0.3
  )

  For EACH institution in the DB:
    ┌─────────────────────────────────────────────────┐
    │ Institution: "Wageningen University and..."     │
    ├─────────────────────────────────────────────────┤
    │ Compares:                                        │
    │   [0.11, ...] <=> DB.name_embedding             │
    │   Name similarity: 0.92                        │
    │                                                 │
    │   [0.89, ...] <=> DB.acronym_embedding          │
    │   Acronym similarity: 0.98                      │
    │                                                 │
    │   Combined: (0.92×0.7) + (0.98×0.3) = 0.938    │
    └─────────────────────────────────────────────────┘
  
  Sort by combined_similarity → Top 5

↓

STEP 3: TIEBREAKER WITH RAPIDFUZZ
  For each of the Top 5:
    
    Cosine (already calculated):  0.938
    
    Fuzz Name:
      "wageningen university" vs "wageningen university and research..."
      → 0.88
    
    Fuzz Acronym:
      "wur" vs "wur"
      → 1.00
    
    FINAL SCORE:
      (0.50 × 0.938) + (0.40 × 0.88) + (0.10 × 1.00) = 0.921

↓

BEST MATCH 🏆
  Institution: "Wageningen University and Research Centre"
  Final Score: 0.921
```

---

## 🎯 What Compares with What - Summary Table

| Stage | Your Input | Compares With | Type of Comparison |
|-------|----------|----------------|---------------------|
| **Embeddings - Name** | Embedding of "Wageningen University" | `name_embedding` of each institution in DB | Cosine similarity of vectors |
| **Embeddings - Acronym** | Embedding of "WUR" | `acronym_embedding` of each institution in DB | Cosine similarity of vectors |
| **RapidFuzz - Name** | "wageningen university" (normalized) | "wageningen university and..." (normalized) | Character similarity (%) |
| **RapidFuzz - Acronym** | "wur" (normalized) | "wur" (normalized) | Character similarity (%) |

---

## 🔧 How Name and Acronym Work

### 1. In the Database (when saving)

```python
# CLARISA Institution
{
  "code": 1,
  "name": "Wageningen University and Research Centre",
  "acronym": "WUR"
}

# Two separate embeddings are generated
name_embedding = get_embedding("Wageningen University and Research Centre")
acronym_embedding = get_embedding("WUR")

# Saved in DB
{
  "clarisa_id": 1,
  "name": "Wageningen University and Research Centre",
  "name_embedding": [1024 numbers],  ← Full NAME embedding
  "acronym": "WUR",
  "acronym_embedding": [1024 numbers]  ← ACRONYM embedding alone
}
```

### 2. In Search (when querying)

#### Option A: Search by name only

```python
search_by_name_embedding("Wageningen University")
```

**Compares:**
- Your embedding of "Wageningen University"
- vs `name_embedding` of all institutions
- ✅ Completely ignores acronyms

#### Option B: Search by acronym only

```python
search_by_acronym_embedding("WUR")
```

**Compares:**
- Your embedding of "WUR"
- vs `acronym_embedding` of all institutions
- ✅ Completely ignores names

#### Option C: Combined Search (RECOMMENDED)

```python
search_combined("Wageningen University", "WUR", name_weight=0.7, acronym_weight=0.3)
```

**Compares:**
- Your embedding of "Wageningen University" vs `name_embedding` → Score A
- Your embedding of "WUR" vs `acronym_embedding` → Score B
- Final Score = (A × 0.7) + (B × 0.3)

**Advantage:** Finds matches even if the name is different but the acronym matches, or vice versa.

---

## 💡 Practical Examples

### Example 1: Similar name, different acronym

```
Query: "World Resources Institute" + "WRI"

Candidate 1: "World Resources Institute" (WRI)
  - Similar name: 1.00 ✅
  - Similar acronym: 1.00 ✅
  - Combined: (1.00×0.7) + (1.00×0.3) = 1.00 🏆

Candidate 2: "World Research Institute" (WRE)
  - Similar name: 0.95 ✅
  - Similar acronym: 0.65 ⚠️
  - Combined: (0.95×0.7) + (0.65×0.3) = 0.86

→ Candidate 1 wins (perfect match)
```

### Example 2: Different name, same acronym

```
Query: "Massachusetts Institute of Technology" + "MIT"

Candidate 1: "MIT" (MIT)
  - Similar name: 0.40 ⚠️ (very short name vs long)
  - Similar acronym: 1.00 ✅
  - Combined: (0.40×0.7) + (1.00×0.3) = 0.58

Candidate 2: "Massachusetts Institute" (MIT)
  - Similar name: 0.92 ✅
  - Similar acronym: 1.00 ✅
  - Combined: (0.92×0.7) + (1.00×0.3) = 0.94 🏆

→ Candidate 2 wins (better name + acronym)
```

### Example 3: Only have the name

```
Query: "Wageningen University" (without acronym)

Use: search_by_name_embedding()

Candidate 1: "Wageningen University and Research Centre"
  - Similar name: 0.92 ✅
  
Candidate 2: "University of Wageningen"
  - Similar name: 0.81

→ Candidate 1 wins
```

---

## 🏛️ Weight Adjustments

You can change how each factor influences:

```python
# Vector search (Supabase)
search_combined(
    name_weight=0.7,      # ← Change: more weight on name
    acronym_weight=0.3    # ← Change: less weight on acronym
)

# Tiebreaker (RapidFuzz)
final_score = (
    0.50 * cosine_sim +   # ← Change: embeddings weight
    0.40 * fuzz_name +    # ← Change: text weight (name)
    0.10 * fuzz_acronym   # ← Change: text weight (acronym)
)
```

### Adjustment example:

If acronyms are very reliable in your data:

```python
# Give more weight to acronym
search_combined(name_weight=0.5, acronym_weight=0.5)

final_score = (
    0.40 * cosine_sim +    # Less weight on embeddings
    0.30 * fuzz_name +     # Less weight on name
    0.30 * fuzz_acronym    # More weight on acronym
)
```

---

## ❓ Frequently Asked Questions

### Why separate name and acronym?

**Advantages:**
1. You can search by one or the other
2. You can adjust weights independently
3. Some institutions have similar names but unique acronyms
4. Allows more flexible searches

**Example:**
- "CGIAR" (acronym) very different from "Consultative Group on International Agricultural Research" (name)
- If you search for "CGIAR", finding it through `acronym_embedding` is more effective

### What happens if an institution doesn't have an acronym?

```python
# In the DB
{
  "name": "Universidad de Buenos Aires",
  "acronym": null,
  "name_embedding": [1024 numbers],
  "acronym_embedding": null  ← Not generated
}

# In combined search
acronym_similarity = COALESCE(..., 0)  # = 0 if null
combined = (0.85×0.7) + (0×0.3) = 0.595
# Only counts the name, acronym = 0
```

### Are embeddings regenerated on every search?

**NO** ❌

- Embeddings of **institutions in DB**: Generated ONCE (when populating)
- Embeddings of **query**: Generated each time you search

```python
# Once (when populating)
populate_clarisa_db.py → generates embeddings of 10,000+ institutions

# Each search (fast)
search_example.py → only generates query embedding (2 vectors)
```

---

Clear? 🎯
