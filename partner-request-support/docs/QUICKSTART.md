# 🚀 Quick Guide - CLARISA Mapping

## Quick Setup (5 steps)

### 1️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 2️⃣ Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your favorite editor
```

**Required variables:**
- `CLARISA_API_URL` - CLARISA API URL
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Supabase key (anon or service role)
- `AWS_ACCESS_KEY_ID_BR` - AWS Access Key (for Bedrock)
- `AWS_SECRET_ACCESS_KEY_BR` - AWS Secret Key (for Bedrock)

### 3️⃣ Create Table in Supabase

1. Open the **SQL Editor** in Supabase
2. Copy and paste the content from `sql/create_clarisa_vector_table.sql`
3. Execute the script

This will create:
- ✅ Table `clarisa_institutions_v2`
- ✅ Vector indexes (ivfflat)
- ✅ 3 RPC functions for search

### 4️⃣ Populate the Database

```bash
python populate_clarisa_db.py
```

**Estimated time:** 10-15 minutes

This script:
1. Downloads ~3000+ institutions from CLARISA
2. Generates embeddings with Amazon Titan (1024 dims)
3. Inserts into Supabase in batches

### 5️⃣ Test Search

```bash
python search_example.py
```

You'll see 4 examples of hybrid search in action.

---

## 📖 Basic Usage

### Simple Search

```python
from search_example import search_institution_hybrid

# Search by name
result = search_institution_hybrid(
    partner_name="Wageningen University",
    threshold=0.4
)

print(result['name'])
print(result['final_score'])
```

### Search with Acronym

```python
result = search_institution_hybrid(
    partner_name="World Resources Institute",
    acronym="WRI",
    threshold=0.4
)
```

---

## 🔍 How Hybrid Search Works

```
Query: "Wageningen University"
    ↓
1. Generate Embedding (Titan) - WITHOUT normalization
   "Wageningen University" → [0.123, 0.456, ...]
    ↓
2. Search Top 5 by Cosine Similarity (Supabase RPC)
   Embeddings in DB are also WITHOUT normalization
    ↓
3. Tiebreak with RapidFuzz - WITH normalization
   "wageningen university" vs "wageningen university and research"
    ↓
Final Score = 50% Cosine + 40% Fuzz Name + 10% Fuzz Acronym
    ↓
Best Match ✨
```

### 📝 Normalization Strategy

**Key:** We use **two normalization levels**:

| Context | Normalization | Function |
|---------|---------------|----------|
| **Embeddings** | ❌ Minimal | Preserves semantics |
| **RapidFuzz** | ✅ Complete | Improves string matching |

```python
# For embeddings (saved in DB)
"Wageningen University and Research Centre (WUR)"  # Original

# For RapidFuzz (when comparing)
"wageningen university and research centre wur"   # Normalized
```

**See:** [docs/NORMALIZATION_STRATEGY.md](docs/NORMALIZATION_STRATEGY.md) for more details.

---

## 📁 Key Files

| File | Purpose |
|------|---------|  
| `populate_clarisa_db.py` | Populate database |
| `search_example.py` | Search examples |
| `src/clarisa_api.py` | CLARISA API client |
| `src/embeddings.py` | Generate embeddings with Titan |
| `src/supabase_client.py` | Supabase functions |
| `sql/create_clarisa_vector_table.sql` | Create table in Supabase |

---

## ⚙️ Advanced Configuration

### Adjust Search Weights

In `search_example.py`, modify:

```python
# Combined score
combined_score = (
    0.50 * cosine_sim +      # ← Adjust this weight
    0.40 * fuzz_name +       # ← Adjust this weight
    0.10 * fuzz_acronym      # ← Adjust this weight
)
```

### Change Threshold

```python
# More restrictive (fewer results, higher precision)
result = search_institution_hybrid(partner_name="...", threshold=0.7)

# More permissive (more results, lower precision)
result = search_institution_hybrid(partner_name="...", threshold=0.3)
```

---

## 🐛 Common Issues

### ❌ ImportError: No module named 'src'

```bash
# Make sure you're in the project root directory
cd clarisa-cgspace_mapping

# Run from there
python populate_clarisa_db.py
```

### ❌ Supabase: relation "clarisa_institutions_v2" does not exist

Execute the SQL script first (Step 3).

### ❌ AWS Bedrock: Access Denied

1. Verify your AWS user has Bedrock permissions
2. Confirm the region is `us-east-1`
3. Verify you have access to model `amazon.titan-embed-text-v2:0`

### ❌ Table is empty

Run `python populate_clarisa_db.py` first.

---

## 📊 Check Status

```python
from src.supabase_client import count_institutions

count = count_institutions()
print(f"Institutions in DB: {count}")
```

---

## 📚 More Information

See [README.md](README.md) for complete documentation.

---

✅ **Ready to start!**
