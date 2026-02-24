# CLARISA - CGSpace Mapping Project

Modularized project for mapping institutions between CLARISA and CGSpace using hybrid vector search (embeddings + RapidFuzz).

## 🏗️ Project Structure

```
clarisa-cgspace_mapping/
├── sql/
│   └── create_clarisa_vector_table.sql    # SQL script to create table in Supabase
├── src/
│   ├── __init__.py
│   ├── clarisa_api.py                     # CLARISA API client
│   ├── embeddings.py                      # Embedding generation with Titan
│   ├── supabase_client.py                 # Supabase client with RPC functions
│   └── utils.py                           # Common utilities
├── populate_clarisa_db.py                 # Script to populate the database
├── search_example.py                       # Hybrid search example
├── config_util.py                         # Credentials configuration
├── mapping_bedrock.py                     # (Legacy) Previous script
├── mapping_clarisa_comparison.py          # (Legacy) Previous script
└── pyproject.toml                         # Project dependencies
```

## 📊 Vector Database in Supabase

### Table Structure `clarisa_institutions_v2`

| Field | Type | Description |
|-------|------|-------------|
| `id` | SERIAL | Auto-incremental ID (PK) |
| `clarisa_id` | INTEGER | CLARISA unique ID (UNIQUE) |
| `name` | TEXT | Institution name |
| `acronym` | TEXT | Acronym |
| `website` | TEXT | Website |
| `countries` | TEXT[] | Countries array |
| `institution_type` | TEXT | Institution type |
| `name_embedding` | vector(1024) | Name embedding |
| `acronym_embedding` | vector(1024) | Acronym embedding |
| `created_at` | TIMESTAMP | Creation date |
| `updated_at` | TIMESTAMP | Last update |

### Available RPC Functions

#### 1. `search_institution_by_name`
Search by name similarity (Top 5)
```sql
SELECT * FROM search_institution_by_name(
    query_embedding := '[...]',
    match_threshold := 0.5,
    match_count := 5
);
```

#### 2. `search_institution_by_acronym`
Search by acronym similarity (Top 5)
```sql
SELECT * FROM search_institution_by_acronym(
    query_embedding := '[...]',
    match_threshold := 0.5,
    match_count := 5
);
```

#### 3. `search_institution_combined`
Combined search with configurable weights
```sql
SELECT * FROM search_institution_combined(
    name_query_embedding := '[...]',
    acronym_query_embedding := '[...]',
    name_weight := 0.7,
    acronym_weight := 0.3,
    match_threshold := 0.5,
    match_count := 5
);
```

## 🔬 Normalization Strategy

This project uses **two levels of normalization** to maximize accuracy:

### 1. Embeddings (Titan) → Minimal Cleaning ✨
- ✅ Preserves original text (accents, capitals)
- ✅ Only normalizes multiple spaces
- 🎯 Modern models understand natural text better

```python
# Text stored in DB with embedding
"Universidad de São Paulo (USP)"  # Original preserved
```

### 2. String Matching (RapidFuzz) → Full Normalization 🔍
- ✅ Lowercase + no accents
- ✅ Full normalization for comparison
- 🎯 Maximizes character matching accuracy

```python
from src.utils import clean_text_for_matching
normalized = clean_text_for_matching("São Paulo")
# "sao paulo"
```

**See:** [docs/NORMALIZATION_STRATEGY.md](docs/NORMALIZATION_STRATEGY.md) for complete details.

## 🛠️🚀 Initial Setup

### 1. Environment Variables

Create a `.env` file with:

```bash
# CLARISA API
CLARISA_API_URL=https://api.clarisa.cgiar.org/api/institutions

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key

# AWS Bedrock (configure in config_util.py)
AWS_ACCESS_KEY_ID_BR=your-access-key
AWS_SECRET_ACCESS_KEY_BR=your-secret-key

# OpenAI (if used for other functions)
OPENAI_API_KEY=your-openai-key
```

### 2. Create the Table in Supabase

Execute the SQL script in Supabase SQL editor:

```bash
# Copy content from sql/create_clarisa_vector_table.sql
# and execute it in Supabase SQL Editor
```

This will create:
- ✅ Table `clarisa_institutions_v2` with vector indexes
- ✅ RPC functions for hybrid search
- ✅ Triggers for automatic updates

### 3. Install Dependencies

```bash
pip install requests python-dotenv supabase tqdm boto3 numpy rapidfuzz
```

## 📥 Populate the Database

### Run the Population Script

```bash
python populate_clarisa_db.py
```

This script:
1. 🔄 Fetches all institutions from the CLARISA API
2. 🧠 Generates embeddings for name and acronym using Amazon Titan
3. 💾 Inserts into Supabase in batches of 50

**Estimated time**: ~10-15 minutes depending on the number of institutions.

## 🔍 Hybrid Search

### Recommended Process

```python
from src.embeddings import get_embedding, embedding_to_list
from src.supabase_client import search_by_name_embedding
from rapidfuzz import fuzz

# 1. Generate query embeddings
partner_name = "Wageningen University"
name_embedding = get_embedding(partner_name)

# 2. Get Top 5 by cosine similarity (Supabase RPC)
candidates = search_by_name_embedding(
    query_embedding=embedding_to_list(name_embedding),
    threshold=0.5,
    limit=5
)

# 3. Tiebreak with RapidFuzz
best_match = None
best_score = 0

for candidate in candidates:
    # Combine cosine similarity + fuzz ratio
    cosine_sim = candidate['similarity']
    fuzz_score = fuzz.ratio(partner_name, candidate['name']) / 100
    
    # Combined score (adjust weights as needed)
    combined_score = (0.6 * cosine_sim) + (0.4 * fuzz_score)
    
    if combined_score > best_score:
        best_score = combined_score
        best_match = candidate

print(f"Best match: {best_match['name']} (score: {best_score:.2f})")
```

## 📝 Module Usage

### Fetch institutions from CLARISA

```python
from src.clarisa_api import get_all_parsed_institutions

institutions = get_all_parsed_institutions()
```

### Generate embeddings

```python
from src.embeddings import get_embedding, cosine_similarity

emb1 = get_embedding("Wageningen University")
emb2 = get_embedding("WUR")

similarity = cosine_similarity(emb1, emb2)
```

### Search in Supabase

```python
from src.supabase_client import search_combined
from src.embeddings import get_embedding, embedding_to_list

name_emb = embedding_to_list(get_embedding("Wageningen University"))
acronym_emb = embedding_to_list(get_embedding("WUR"))

results = search_combined(
    name_embedding=name_emb,
    acronym_embedding=acronym_emb,
    name_weight=0.7,
    acronym_weight=0.3,
    threshold=0.4,
    limit=10
)
```

## 🧪 Complete Example

See `search_example.py` for a complete hybrid search example.

## ⚙️ Customization

### Adjust Search Weights

In the `search_combined` function, you can adjust:
- `name_weight`: Name weight (default: 0.7)
- `acronym_weight`: Acronym weight (default: 0.3)
- `threshold`: Minimum similarity threshold (default: 0.5)

### Change Batch Size

In `populate_clarisa_db.py`:
```python
populate_clarisa_institutions(batch_size=100)  # Default: 50
```

## 🐛 Troubleshooting

### Error: "relation clarisa_institutions_v2 does not exist"
- ✅ Run the SQL script in Supabase first

### Error: "embedding dimension mismatch"
- ✅ Verify you're using Amazon Titan v2 (1024 dimensions)

### Embeddings are very slow
- ✅ Reduce `batch_size` in the population script
- ✅ Verify your AWS region (use `us-east-1`)

## 📚 Next Steps

1. ✅ Table created with separate embeddings
2. ✅ Automated population scripts
3. 🔄 Implement complete hybrid search
4. 🔄 REST API for searches
5. 🔄 Monitoring dashboard

## 📄 License

CGIAR internal project
