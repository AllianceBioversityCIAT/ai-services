# CLARISA-Agresso Institution Mapping

A Python application for mapping institutions between CLARISA (CGIAR Level Agricultural Results Interoperable System Architecture) and Agresso using vector embeddings and semantic matching.

## Project Overview

This tool provides automated mapping between institution records from Agresso and the CLARISA institutions database. It uses two different approaches:

1. **Supabase Vector Database**: Uses AWS Bedrock embeddings stored in Supabase for semantic matching
2. **OpenSearch API**: Directly queries the CLARISA OpenSearch API for institution matching

## Features

- Reads institution data from Agresso Excel files
- Fetches institution data from CLARISA API
- Generates text embeddings using AWS Bedrock Titan model
- Stores embeddings in Supabase vector database
- Performs semantic matching between institutions
- Generates Excel reports with match results
- Comprehensive logging

## Requirements

- Python 3.13+
- Dependencies listed in `pyproject.toml`

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/clarisa-agresso_mapping.git
cd clarisa-agresso_mapping
```

2. Create a virtual environment and install dependencies:

```bash
uv venv
source .venv/bin/activate  # On Windows: venv\Scripts\activate
uv pip install -r pyproject.toml
```

## Configuration

Create a `.env` file in the project root with the following variables:

```
# AWS Bedrock credentials
AWS_ACCESS_KEY_ID_BR=your_aws_access_key
AWS_SECRET_ACCESS_KEY_BR=your_aws_secret_key

# CLARISA API configuration
CLARISA_API_URL=https://api.clarisa.cgiar.org/api/institutions
CLARISA_BEARER_TOKEN=your_bearer_token

# Supabase configuration
SUPABASE_URL=your_supabase_url
```

## Usage

Run the application by executing the main script:

```bash
uv run python main.py
```

By default, the application uses the Supabase vector database method. To switch to OpenSearch, modify the `db` variable in `main.py`:

```python
db = "opensearch"  # Change to "supabase" for Supabase method
```

### Input File Format

The application expects an Excel file in `app/utils/resources/` named `agresso_institution_list_20250512_MA.xlsx` containing at least these columns:

- `agreso_institution_id` (ID from Agresso)
- `agreso_institucion_name` (Institution name from Agresso)

### Output

Results are saved to Excel files in the `app/utils/resources/` directory:

- `results_matches_sb.xlsx` for Supabase method results
- `results_matches_os.xlsx` for OpenSearch method results

Both files include columns for:
- Agresso Institution name
- Matched CLARISA institution name
- Matching score
- CLARISA institution ID

## Project Structure

```
├── main.py                  # Main entry point
├── pyproject.toml           # Project dependencies
├── app/
│   ├── mapping/             # Mapping functionality
│   │   ├── mapping_supabase.py     # Supabase vector mapping method
│   │   ├── mapping_opensearch.py   # OpenSearch API mapping method 
│   │   └── vectorize_db.py         # Vector embedding utilities
│   └── utils/
│       ├── config/          # Configuration utilities
│       ├── logger/          # Logging utilities
│       └── resources/       # Data resources (Excel files)
├── data/
│   └── logs/                # Application logs
├── .venv/
├── .env
└── README.md
```

## How It Works

### Supabase Method

1. Reads institution data from the Agresso Excel file
2. Fetches institution data from CLARISA API
3. Generates text embeddings using AWS Bedrock for CLARISA institutions
4. Stores embeddings in Supabase vector database
5. For each Agresso institution:
   - Generates embedding using AWS Bedrock
   - Performs cosine similarity search against stored CLARISA embeddings
   - Computes textual similarity score as additional matching metric
6. Saves results to Excel file

### OpenSearch Method

1. Reads institution data from the Agresso Excel file
2. For each Agresso institution:
   - Queries the CLARISA OpenSearch API directly
   - Retrieves the best match based on the search score
3. Saves results to Excel file

## Logging

The application logs information to both console and file:
- Console for real-time feedback
- Rotating log files stored in `data/logs/app.log`