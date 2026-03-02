# Web Search Fallback Feature

## 📖 Description

When the system doesn't find a match in CLARISA for an institution, it automatically searches for information on the internet using **OpenAI Web Search API**. This allows collecting official data from institutions that are not yet in the CLARISA database.

## 🎯 Objective

- Reduce the number of institutions without matches
- Obtain official information from reliable sources
- Provide data for subsequent manual validation
- Facilitate the incorporation of new institutions into CLARISA

## 🔧 Configuration

### 1. OpenAI API Key

Add your API key to the `.env` file:

```bash
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
```

You can obtain your API key at: https://platform.openai.com/api-keys

### 2. Enable/Disable Web Search

In `mapping_clarisa_comparison.py`, modify the constant:

```python
ENABLE_WEB_SEARCH = True   # Enable web search
ENABLE_WEB_SEARCH = False  # Disable web search
```

### 3. Install Dependencies

```bash
pip install openai>=1.10.0
```

## 📊 Excel Format

To take full advantage of web search, the Excel file should have the following columns:

| Column | Name | Description | Required |
|--------|------|-------------|----------|
| 0 | ID | Unique identifier | Optional |
| 1 | partner_name | Institution name | **Required** |
| 2 | acronym | Acronym | Optional |
| 3 | country | Country | Optional* |
| 4 | website | Official website | Optional* |

> *Optional but **highly recommended** to improve web search accuracy.

### Example:

| ID | partner_name | acronym | country | website |
|----|--------------|---------|---------|---------|
| 1 | Stanford University | SU | United States | https://www.stanford.edu |
| 2 | CIMMYT | CIMMYT | Mexico | https://www.cimmyt.org |
| 3 | Instituto Nacional de Investigación Agropecuaria | INIA | Uruguay | https://www.inia.uy |

## 🔍 Search Strategy

The system uses a dual strategy:

### Strategy 1: Focused Search (with website)

If a website is provided, the search is limited **only to that domain**:

```python
tools=[{
    "type": "web_search",
    "filters": {
        "allowed_domains": ["stanford.edu"]
    }
}]
```

**Advantages:**
- ✅ Official and reliable information
- ✅ Faster (fewer pages)
- ✅ Reduces model hallucinations
- ✅ Higher precision

### Strategy 2: Open Search (without website)

If there's no website, searches the internet openly:

```python
tools=[{"type": "web_search"}]
```

The query includes:
- Institution name
- Country (if available)
- Prioritization of official sources (.edu, .org, .gov)

## 📤 Columns Added to Output

The system adds 3 new columns to the results Excel:

| Column | Description | Example |
|---------|-------------|---------|
| `WEB_SEARCH_PERFORMED` | If web search was performed | `True` / `False` |
| `WEB_SEARCH_RESULT` | Extracted information | "Official name: Stanford University\nCountry: United States\n..." |
| `WEB_SEARCH_SOURCES` | URLs used | "https://www.stanford.edu/about \| https://www.stanford.edu/contact" |

## 📋 Extracted Information

For each institution without a match, the system extracts structured information according to **CGIAR validation rules**:

### 1. Basic Information
- **Official full name** - Complete official name
- **Acronym** - Acronym (if exists)
- **Country** - Country or location
- **Official website** - Official website

### 2. Legal Status
- **Is it a legal entity?** - Whether the institution is a legal entity
- **Parent organization** - If not a legal entity, what is its affiliated organization that is
  - *Example: "Earth Institute" → "Columbia University"*

### 3. Institution Type (clasificación específica CGIAR)
- University or academic institution
- National/local research institution
- International/regional research institution
- Government entity (ministry/department/agency)
- Bilateral development agency (USAID, DFID, etc.)
- International/regional financial institution (World Bank, Asian Development Bank, etc.)
- International organization (UN entities)
- NGO
- Private company or commercial entity

### 4. Research Mandate
- **Significant research mandate?** - Whether it has a significant research mandate
- **Main activities** - Brief description of activities and focus areas

> **Note:** This information allows subsequent validation of whether the institution meets CGIAR eligibility criteria to be added to CLARISA.

## 💰 Cost Estimation

| Model | Approximate cost per search | Notes |
|--------|-------------------------------|-------|
| GPT-4o | ~$0.02 - 0.03 | Recommended (current) |
| GPT-4.5 | ~$0.03 - 0.05 | Higher precision |

**Example:** For 100 institutions without matches:
- Estimated cost: $2 - $3 USD

## 📊 Web Search Statistics

At the end of the pipeline, you'll see statistics like:

```
📈 Statistics:
   Total processed:      150
   ✅ Successful matches: 100 (66.7%)
   ❌ No match:           50 (33.3%)
   🌐 Web search:         45/50 successful
   ⚠️  Errors:             0
```

## 🔬 Usage Example

### Python Code

```python
from src.web_search import test_search

# Test with website (focused search)
test_search(
    name="Stanford University",
    country="United States",
    website="https://www.stanford.edu"
)

# Test without website (open search)
test_search(
    name="Instituto de Investigaciones Agropecuarias",
    country="Chile"
)
```

**See more examples:** [WEB_SEARCH_EXAMPLES.md](WEB_SEARCH_EXAMPLES.md) - Detailed examples with different types of institutions

### Complete Pipeline

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Configure .env with OPENAI_API_KEY

# 3. Run pipeline
python mapping_clarisa_comparison.py
```

## 🎯 Use Cases

### ✅ When to use Web Search:

1. **Local institutions** - Regional universities or research centers
2. **New organizations** - Recent institutions not in CLARISA
3. **Name variations** - When Spanish/English names differ
4. **Manual validation** - To collect data before adding to CLARISA

### ❌ When NOT to use Web Search:

1. **Complete databases** - If CLARISA has very good coverage
2. **Limited budget** - If budget is very restricted
3. **Sensitive data** - If there are privacy restrictions
4. **High speed required** - Web search adds latency (~3-5s per search)

## 🛠️ Troubleshooting

### Error: "OpenAI API key not found"

**Solution:** Verify that `OPENAI_API_KEY` is in your `.env` file:

```bash
echo $OPENAI_API_KEY  # Should display your key
```

### Error: "Rate limit exceeded"

**Solution:** OpenAI has rate limits. Options:
1. Add delay between requests
2. Use a higher OpenAI tier
3. Process in smaller batches

### Web Search doesn't find anything

**Possible causes:**
1. Institution name too generic or ambiguous
2. Institution without official web presence
3. Provided website is incorrect

**Solution:** Manually review cases and verify input data.

## 🚀 Future Improvements

~~Search query will be updated to include:~~

- ✅ **IMPLEMENTED:** CGIAR rules for permitted institutions
- ✅ **IMPLEMENTED:** Specific institution type validation
- ✅ **IMPLEMENTED:** Legal entity status extraction
- ✅ **IMPLEMENTED:** Affiliated organization identification
- ⏳ Source reliability scoring (future)
- ⏳ Automatic eligibility validation (future)

> **Update (March 2, 2026):** Queries now incorporate official CGIAR rules for institution validation. See [CGIAR_INSTITUTION_RULES.md](CGIAR_INSTITUTION_RULES.md) for complete details.

## 📚 Referencias

- [OpenAI Web Search Documentation](https://developers.openai.com/api/docs/guides/tools-web-search/)
- [OpenAI API Keys](https://platform.openai.com/api-keys)
- [OpenAI Pricing](https://openai.com/api/pricing/)
