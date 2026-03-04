# 🚀 How to Execute Institution Mapping

## 📋 Summary

This script processes an Excel file with institutions and maps them automatically to CLARISA using hybrid search (vector embeddings + RapidFuzz).

---

## ✅ Prerequisites

### 1. Populated Database

```bash
# If you haven't done it yet
python populate_clarisa_db.py
```

This should have created ~10,000+ institutions in Supabase with their embeddings.

### 2. Prepared Excel File

Your Excel must have **at least 3 columns** in this order:

| Column | Name          | Required | Description                    |
|--------|---------------|----------|--------------------------------|
| 0      | ID            | No       | Identifier (e.g.: cgspace_id)  |
| 1      | partner_name  | **YES**  | Institution name               |
| 2      | acronym       | No       | Acronym (e.g.: WUR, MIT)       |

**Example:**

| id  | partner_name                            | acronym |
|-----|-----------------------------------------|---------|
| 123 | Wageningen University and Research      | WUR     |
| 456 | Massachusetts Institute of Technology   | MIT     |
| 789 | World Resources Institute               | WRI     |

---

## 🎯 Run the Pipeline

### Step 1: Configure the Excel File

Edit [mapping_clarisa_comparison.py](mapping_clarisa_comparison.py) line ~265:

```python
excel_file = "File To Dani (1).xlsx"  # ← Change this to your file
```

### Step 2: Execute

```bash
python mapping_clarisa_comparison.py
```

### Step 3: Review Results

The script will generate: `clarisa_mapping_results.xlsx`

---

## 📊 Excel Output

The results file will include the original columns PLUS:

| Column                | Description                                    |
|-----------------------|------------------------------------------------|
| `MATCH_FOUND`         | True/False - whether a match was found         |
| `CLARISA_ID`          | CLARISA ID of the match                        |
| `CLARISA_NAME`        | Full institution name in CLARISA               |
| `CLARISA_ACRONYM`     | Acronym in CLARISA                             |
| `CLARISA_COUNTRIES`   | Countries where it operates                    |
| `CLARISA_TYPE`        | Institution type                               |
| `CLARISA_WEBSITE`     | Website                                        |
| `COSINE_SIMILARITY`   | Vector similarity score (0-1)                  |
| `FUZZ_NAME_SCORE`     | Text similarity score for name (0-1)           |
| `FUZZ_ACRONYM_SCORE`  | Text similarity score for acronym (0-1)        |
| `FINAL_SCORE`         | Final combined score (0-1)                     |
| `MATCH_QUALITY`       | excellent/good/fair/no_match                   |

---

## ⚙️ Advanced Configuration

You can adjust the parameters at the beginning of [mapping_clarisa_comparison.py](mapping_clarisa_comparison.py):

```python
# Lines 18-26
THRESHOLD_EMBEDDINGS = 0.3   # Lower = more candidates
THRESHOLD_FINAL = 0.5        # Minimum score for valid match
NAME_WEIGHT = 0.7            # Name weight (0-1)
ACRONYM_WEIGHT = 0.3         # Acronym weight (0-1)
COSINE_WEIGHT = 0.50         # Embeddings weight in final score
FUZZ_NAME_WEIGHT = 0.40      # Name text weight in final score
FUZZ_ACRONYM_WEIGHT = 0.10   # Acronym text weight in final score
```

### Adjustment Examples:

**More restrictive (fewer matches, higher precision):**
```python
THRESHOLD_FINAL = 0.7  # Only matches with 70%+ score
```

**More permissive (more matches, lower precision):**
```python
THRESHOLD_FINAL = 0.4  # Accept matches with 40%+ score
```

**Prioritize acronyms:**
```python
NAME_WEIGHT = 0.5
ACRONYM_WEIGHT = 0.5
# And in final score:
FUZZ_ACRONYM_WEIGHT = 0.20  # Double acronym weight
FUZZ_NAME_WEIGHT = 0.30     # Reduce name weight
```

---

## 📈 Results Interpretation

### Match Quality

- **excellent** (≥0.85): Very reliable match, review only exceptional cases
- **good** (≥0.70): Reliable match, review some cases
- **fair** (≥0.50): Acceptable match, **review manually**
- **no_match**: No match found above threshold

### Individual Scores

**COSINE_SIMILARITY** (vector similarity):
- > 0.90: Virtually identical semantically
- 0.70-0.90: Very similar
- 0.50-0.70: Moderately similar
- < 0.50: Not very similar

**FUZZ_NAME_SCORE** (text similarity):
- 1.00: Identical text
- > 0.80: Very similar
- 0.50-0.80: Partially similar
- < 0.50: Different

**FINAL_SCORE** (combination of both):
- The score used to determine the match
- Combines semantics + text + acronym

---

## 🎯 Process Flow

```
For each row in the Excel:
  ↓
1. Read partner_name and acronym
  ↓
2. Generate embeddings with Amazon Titan
  ↓
3. Search Top 5 candidates in Supabase
   (using cosine similarity of embeddings)
  ↓
4. Refine with RapidFuzz (text comparison)
  ↓
5. Calculate final combined score
  ↓
6. If score ≥ THRESHOLD_FINAL → MATCH
   If score < THRESHOLD_FINAL → NO MATCH
```

---

## 💡 Tips

### 1. Review "fair" matches

Matches with "fair" quality (0.50-0.70) should be manually reviewed:

```python
# Filter in pandas afterwards
import pandas as pd
df = pd.read_excel("clarisa_mapping_results.xlsx")
review = df[df['MATCH_QUALITY'] == 'fair']
review.to_excel("manual_review.xlsx", index=False)
```

### 2. Verify no match

Institutions without a match may need:
- Manual search in CLARISA
- Lower threshold adjustment
- Verify they exist in CLARISA

### 3. Process in batches

If you have many institutions (>1000), process in batches:

```python
# In mapping_clarisa_comparison.py
df = pd.read_excel(excel_file)
batch = df.head(100)  # First 100
batch.to_excel("batch_1.xlsx", index=False)

# Then process batch_1.xlsx
```

---

## 🐛 Troubleshooting

### Error: "The database is empty"

```bash
# Run first
python populate_clarisa_db.py
```

### Error: "Excel file not found"

Verify the file path in `mapping_clarisa_comparison.py` line ~265.

### Many "no_match"

Try:
1. Lower `THRESHOLD_FINAL` to 0.4 or 0.3
2. Verify names in Excel are correct
3. Check that CLARISA DB is complete

### Incorrect matches

Try:
1. Raise `THRESHOLD_FINAL` to 0.6 or 0.7
2. Adjust weights (more weight on acronyms if they are reliable)
3. Review text normalization

---

## 📚 Related Documentation

- [README.md](README.md) - General project documentation
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide
- [docs/COMO_FUNCIONA_LA_BUSQUEDA.md](docs/COMO_FUNCIONA_LA_BUSQUEDA.md) - Technical explanation of search
- [search_example.py](search_example.py) - API usage examples

---

## ✅ Complete Example

```bash
# 1. Prepare Excel (columns: id, partner_name, acronym)
# 2. Ensure DB is populated
python populate_clarisa_db.py  # If you haven't done it before

# 3. Configure file in mapping_clarisa_comparison.py
# excel_file = "my_file.xlsx"

# 4. Execute
python mapping_clarisa_comparison.py

# 5. Review results
# clarisa_mapping_results.xlsx
```

**Expected output:**
```
🚀 MAPPING PIPELINE: CGSpace → CLARISA
✅ Database ready: 10,237 institutions in CLARISA
📊 Loading Excel file: File To Dani (1).xlsx
✅ 500 rows loaded

Searching for matches: 100%|███████████████| 500/500

📊 RESULTS
✅ File saved: clarisa_mapping_results.xlsx

📈 Statistics:
   Total processed:     500
   ✅ Successful matches: 420 (84.0%)
   ❌ No match:          80 (16.0%)
   
🏆 Match quality:
   Excellent (≥0.85): 350 (83.3%)
   Good (≥0.70):     50 (11.9%)
   Fair (≥0.50):     20 (4.8%)

✅ PROCESS COMPLETED
```

---

Ready to process your institutions? 🚀
