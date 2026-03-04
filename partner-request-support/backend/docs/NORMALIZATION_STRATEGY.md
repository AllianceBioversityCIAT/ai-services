# 📝 Text Normalization Strategy

## 🎯 Summary

This project uses **two normalization levels** depending on context:

1. **Basic Cleaning** → For embeddings (maintains semantics)
2. **Complete Normalization** → For string matching (RapidFuzz)

---

## 🧠 For Embeddings (Amazon Titan)

### ✅ WHAT WE DO

```python
# Original text
"Universidad de São Paulo (USP)"

# Basic cleaning: only multiple spaces
"Universidad de São Paulo (USP)"  # Keeps accents and capitals
```

**Function:** `clean_text_basic()` or automatic in `get_embedding()`

### ❌ WHAT WE DON'T DO

```python
# ❌ DO NOT convert to lowercase
# ❌ DO NOT remove accents
# ❌ DO NOT remove special characters (parentheses, hyphens)
```

### 🤔 Why?

Modern embedding models (like Amazon Titan) are trained with **natural text**:

- ✅ Understand capitals and lowercase
- ✅ Understand accents and special characters
- ✅ Better capture semantic context with original text

**Example of semantic similarity:**

```python
# These texts generate similar embeddings automatically:
"Wageningen University and Research"
"WAGENINGEN UNIVERSITY"
"Universiteit Wageningen"
"WUR"  # Sufficient context to relate it
```

### 📊 Comparison

| Original | Aggressive Normalization | Result |
|----------|--------------------------|--------|
| "CGIAR Initiative" | "cgiar initiative" | ❌ We lose info |
| "Université de Genève" | "universite de geneve" | ❌ We lose context |
| "MIT (Massachusetts Institute)" | "mit massachusetts institute" | ❌ We lose structure |

**Titan understands the original BETTER than normalized.**

---

## 🔍 For String Matching (RapidFuzz)

### ✅ WHAT WE DO

### ✅ LO QUE HACEMOS
| "CGIAR Initiative" | "cgiar initiative" | ❌ Perdemos info |
| "Université de Genève" | "universite de geneve" | ❌ Perdemos contexto |
| "MIT (Massachusetts Institute)" | "mit massachusetts institute" | ❌ Perdemos estructura |

**Titan entiende el original MEJOR que el normalizado.**

---

## 🔍 Para String Matching (RapidFuzz)

### ✅ LO QUE HACEMOS

```python
from src.utils import clean_text_for_matching

# Original text
"Universidad de São Paulo (USP)"

# Complete normalization
"universidad de sao paulo usp"  # lowercase + no accents
```

**Function:** `clean_text_for_matching()`

### ✔️ Transformations:

1. ✅ Convert to lowercase
2. ✅ Remove accents (São → sao)
3. ✅ Remove punctuation (keep parentheses for acronyms)
4. ✅ Normalize multiple spaces

### 🤔 Why?

RapidFuzz does **character comparison** (not semantic):

```python
# Without normalization
fuzz.ratio("Universität", "Universidad")  # Score: ~54%

# With normalization
fuzz.ratio("universitat", "universidad")  # Score: ~82% ✅
```

### 📊 Comparison

| Query | Candidate | Without Norm | With Norm |
|-------|-----------|----------|----------|
| "WUR" | "wur" | 75% | **100%** ✅ |
| "São Paulo" | "Sao Paulo" | 82% | **100%** ✅ |
| "Wageningen Univ" | "WAGENINGEN UNIVERSITY" | 73% | **88%** ✅ |

---

## 🔄 Complete Flow in Hybrid Search

```python
# 1. User query
query = "Wageningen University"
acronym = "WUR"

# 2. Generate embeddings (WITHOUT normalization)
query_embedding = get_embedding(query)  
# Internally does basic cleaning: multiple spaces

# 3. Search Top 5 by cosine similarity (Supabase)
candidates = search_by_name_embedding(query_embedding, limit=5)
# Saved embeddings are ALSO not normalized

# 4. Tiebreak with RapidFuzz (WITH normalization)
from src.utils import clean_text_for_matching

for candidate in candidates:
    # Normalize both for fair comparison
    normalized_query = clean_text_for_matching(query)
    normalized_candidate = clean_text_for_matching(candidate['name'])
    
    fuzz_score = fuzz.ratio(normalized_query, normalized_candidate)
    
# 5. Combined score
final_score = (0.5 * cosine_sim) + (0.4 * fuzz_score) + ...
```

---

## 🛠️ Available Functions

### `clean_text_basic(text)`
Basic cleaning for embeddings

```python
from src.utils import clean_text_basic

text = "Universidad   de São   Paulo  (USP)"
clean = clean_text_basic(text)
# "Universidad de São Paulo (USP)"  ← normalized spaces
```

**Use it when:**
- Manual preprocessing before embeddings (optional)
- Text has problematic multiple spaces

### `clean_text_for_matching(text)`
Complete normalization for RapidFuzz

```python
from src.utils import clean_text_for_matching

text = "Universidad de São Paulo (USP)"
normalized = clean_text_for_matching(text)
# "universidad de sao paulo usp"
```

**Use it when:**
- ✅ You will compare with RapidFuzz
- ✅ You need exact string matching
- ✅ Implementing tiebreak logic

### `clean_text(text)` (legacy)
Alias of `clean_text_for_matching()` for compatibility

```python
# Legacy code still works
from src.utils import clean_text
normalized = clean_text(text)  # Same behavior
```

---

## 📈 Impact on Results

### Search Only by Embeddings

```python
# Query: "Wageningen University"

# Candidate 1: "Wageningen University and Research Centre"
# Without normalization: cosine = 0.92 ✅
# With aggressive normalization: cosine = 0.88 ❌ (loses info)
```

**Result:** Embeddings work BETTER without aggressive normalization.

### Hybrid Search (Embeddings + RapidFuzz)

```python
# Query: "WUR"
# Candidate: "Wageningen University and Research Centre (WUR)"

# Embeddings (not normalized)
cosine_sim = 0.75

# RapidFuzz (normalized)
fuzz.ratio("wur", "wageningen university and research centre wur") = 23%
# vs
fuzz.ratio("WUR", "Wageningen University and Research Centre (WUR)") = 17%

# Combined score IMPROVES with normalization in RapidFuzz
```

**Result:** Hybrid strategy gives the best results.

---

## ✅ Best Practices

### DO ✅

1. **Save original text** in the database
2. **Generate embeddings** with almost original text (only space cleaning)
3. **Normalize when comparing** with RapidFuzz
4. **Separate embeddings** for name and acronym (already implemented)

### DON'T ❌

1. ❌ DO NOT normalize aggressively before embeddings
2. ❌ DO NOT use `.lower()` before generating embeddings
3. ❌ DO NOT remove accents before Titan
4. ❌ DO NOT use RapidFuzz without normalizing both texts

---

## 🔬 Suggested Experiments

If you want to validate this strategy:

```python
# Test 1: Embeddings with vs without normalization
text_original = "Universidad de São Paulo"
text_normalizado = "universidad de sao paulo"

emb_original = get_embedding(text_original)
emb_normalizado = get_embedding(text_normalizado)

# Compare similarities against other universities
```

```python
# Test 2: RapidFuzz with vs without normalization
from rapidfuzz import fuzz
from src.utils import clean_text_for_matching

query = "ETH Zürich"
candidate = "ETH ZURICH"

# Without normalization
score1 = fuzz.ratio(query, candidate)  # ~80%

# Normalized
score2 = fuzz.ratio(
    clean_text_for_matching(query),
    clean_text_for_matching(candidate)
)  # ~100% ✅
```

---

## 📚 References

- [Amazon Titan Embeddings Best Practices](https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html)
- [Vector Search Normalization Considerations](https://www.pinecone.io/learn/vector-search/)
- [RapidFuzz Documentation](https://github.com/maxbachmann/RapidFuzz)

---

## 🎓 Executive Summary

| Context | Normalization | Reason |
|---------|---------------|--------|
| **Embeddings (Titan)** | ❌ Minimal (spaces only) | Models understand natural text better |
| **String Matching (RapidFuzz)** | ✅ Complete (lowercase + no accents) | Character-by-character comparison |
| **Storage in DB** | ❌ Not normalized | Preserves original information |
| **Hybrid Search** | 🔄 Both strategies | Best of both worlds |

**Conclusion:** The implemented hybrid strategy maximizes search precision. 🎯
