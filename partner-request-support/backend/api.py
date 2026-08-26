"""
FastAPI server for Partner Request Support
Handles Excel file upload and processing
"""
import os
import io
import boto3
import uvicorn
import tempfile
import requests
import pandas as pd
from pydantic import BaseModel
from dotenv import load_dotenv
from config.config_util import BR
from typing import List, Dict, Optional
from logger.logger_util import get_logger
from botocore.exceptions import ClientError
from fastapi.middleware.cors import CORSMiddleware
from src.notifications import notify_manual_review_pending
from fastapi.responses import JSONResponse, StreamingResponse
from src.populate_clarisa_db import sync_clarisa_institutions
from fastapi import FastAPI, File, UploadFile, HTTPException, Body, Form
from src.mapping_clarisa_comparison import process_partners_to_json, search_institution_for_excel
from src.web_search import search_institution_online, search_institution_auto_decision, check_same_institution
from src.supabase_client import get_cached_results_by_name, cache_results_batch, count_institutions, check_supabase_connection, clear_all_cache


logger = get_logger()
load_dotenv()

synced_partner_requests: List[Dict] = []

CLARISA_API_URL = os.getenv("CLARISA_PARTNER_REQUESTS_URL") or ""
CLARISA_CREATE_URL = os.getenv("CLARISA_CREATE_URL") or ""
CLARISA_RESPOND_URL = os.getenv("CLARISA_RESPOND_URL") or ""
CLARISA_COUNTRIES_URL = os.getenv("CLARISA_COUNTRIES_URL") or ""
CLARISA_INSTITUTION_TYPES_URL = os.getenv("CLARISA_INSTITUTION_TYPES_URL") or ""

app = FastAPI(
    title="Partner Request Support API",
    description="""
    Partner Request Support API
    
    Overview:
    
    This API provides intelligent matching and processing of partner institution requests
    against the CLARISA (Common List of Agricultural Research Institutions and Services) database.
    
    Key Features:
    
    - 🤖 AI-Powered Matching: Uses semantic embeddings and similarity search for accurate institution matching
    - 📊 Excel Processing: Upload and process batch partner requests from Excel files
    - 🔄 Auto-Synchronization: Keeps local database synchronized with CLARISA
    - 💾 Smart Caching: Reduces processing time with intelligent result caching
    - 🌐 Web Search Integration: Validates matches with AI-powered web research
    - 📈 Quality Scoring: Provides match quality ratings (excellent, good, fair, no match)
    
    Typical Workflow:
    
    Option 1: Excel File Processing
    1. Download the template using `/api/download-template`
    2. Fill in partner institution details
    3. Upload and process via `/api/process-partners`
    4. Review matches and quality scores
    5. Perform manual web searches if needed
    
    Option 2: API Partner Requests
    1. Sync pending requests from CLARISA: `/api/sync-partner-requests`
    2. Process synced requests: `/api/process-api-partners`
    3. Review matches and respond: `/api/respond-partner-request`
    
    Authentication:
    
    Most endpoints require a CLARISA authentication token passed in the request body or headers.
    
    Match Quality Interpretation:
    
    - Excellent (>0.85): High confidence - typically safe to accept
    - Good (0.75-0.85): Probable match - review recommended
    - Fair (0.65-0.75): Possible match - verification required
    - No Match (<0.65): No suitable candidate found
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "🔧 Development (Local)"
        },
        {
            "url": "https://hw4qszwcz55trf2n4xg7ujef7y0tgtya.lambda-url.us-east-1.on.aws",
            "description": "🧪 Testing"
        },
        {
            "url": "https://eff4b5tkftulww4nllaebunmri0cdwrf.lambda-url.us-east-1.on.aws",
            "description": "🚀 Production"
        }
    ],
    openapi_tags=[
        {
            "name": "Health",
            "description": "Health check and status endpoints"
        },
        {
            "name": "Partner Processing",
            "description": "Core endpoints for processing and matching partner institutions"
        },
        {
            "name": "Synchronization",
            "description": "Database and API synchronization operations"
        },
        {
            "name": "Web Search",
            "description": "Manual web search for institution verification"
        },
        {
            "name": "Templates",
            "description": "Download Excel templates and resources"
        },
        {
            "name": "Automated Processing",
            "description": "Fully automated partner request evaluation with AI-driven accept/reject decisions"
        }
    ]
)

_cors_origins = (os.getenv("CORS_ORIGINS") or "https://d2xsau6p4hnevy.cloudfront.net,http://localhost:3000,http://localhost:3001").strip().split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# PYDANTIC MODELS — Automated Processing
# ============================================================================

class AutoPartnerRequest(BaseModel):
    partner_name: str
    country: Optional[str] = None
    website: Optional[str] = None
    acronym: Optional[str] = None
    institution_type: Optional[str] = None
    institution_subtype: Optional[str] = None
    # Fields for responding to an existing CLARISA request
    request_id: Optional[int] = None
    auth_token: Optional[str] = None
    user_id: Optional[int] = None
    auto_respond: bool = False
    # Fields for creating a new CLARISA request (create_in_clarisa=True)
    create_in_clarisa: bool = False
    external_user_mail: Optional[str] = None
    external_user_name: Optional[str] = None
    external_user_comments: Optional[str] = None
    mis_acronym: str = "CLARISA"


class AutoPartnerResponse(BaseModel):
    decision: str  # "ACCEPT" | "REJECT" | "MANUAL_REVIEW"
    confidence: str
    reason: str
    match_quality: str  # "excellent" | "very_good" | "good" | "fair" | "no_match"
    clarisa_match: Optional[Dict] = None
    web_search_performed: bool
    web_search_result: Optional[Dict] = None
    auto_responded_to_clarisa: bool = False
    clarisa_response: Optional[Dict] = None
    duplicate_check_performed: bool = False
    duplicate_check_result: Optional[Dict] = None
    fields_complete: Optional[bool] = None
    missing_fields: Optional[List[str]] = None
    notifications: Optional[Dict] = None


# Auto-decision match-quality thresholds — scoped ONLY to /api/auto-partner-request.
# Independent from mapping_clarisa_comparison.py's own excellent/good/fair/no_match
# thresholds, which the manual-review frontend flow relies on and which are NOT changed.
AUTO_EXCELLENT_MIN = 0.95   # score > this            -> excellent
AUTO_VERY_GOOD_MIN = 0.85   # 0.85 <= score <= 0.95   -> very_good
AUTO_GOOD_MIN = 0.70        # 0.70 <= score < 0.85    -> good
# fair      = 0.60 <= score < 0.70 (exactly what search_institution_for_excel already
#             returns as best_match, since its own THRESHOLD_FINAL == 0.60)
# no_match  = search_result["best_match"] is None (score < 0.60)


def _check_completeness(body: "AutoPartnerRequest"):
    """
    Field-completeness gate for auto-approval (Reglas_Aprobacion_Partners_CLARISA
    V1.1, 6.4), applied to every branch that can result in an auto-approval:
    Name, Type, Subtype, Country (HQ) and Website are required; Acronym is the
    one field allowed to be missing.
    """
    required = {
        "partner_name": body.partner_name,
        "institution_type": body.institution_type,
        "institution_subtype": body.institution_subtype,
        "country": body.country,
        "website": body.website,
    }
    missing = [field for field, value in required.items() if not (value and str(value).strip())]
    return (len(missing) == 0, missing)


@app.get("/", tags=["Health"])
async def root():
    """
    # API Information Endpoint
    
    Returns basic information about the Partner Request Support API.
    
    ## Response
    - **name**: API name
    - **version**: Current API version
    - **status**: Current operational status
    
    ## Example Response
    ```json
    {
        "name": "Partner Request Support API",
        "version": "1.0.0",
        "status": "online"
    }
    ```
    """
    return {
        "name": "Partner Request Support API",
        "version": "1.0.0",
        "status": "online"
    }


@app.get("/health", tags=["Health"])
async def health():
    """
    # Health Check Endpoint
    
    Verifies that the API service is running and healthy.
    Used for monitoring and load balancer health checks.
    
    ## Response
    Returns a simple status indicator.
    
    ## Example Response
    ```json
    {
        "status": "healthy"
    }
    ```
    
    ## HTTP Status Codes
    - **200**: Service is healthy and operational
    """
    return {"status": "healthy"}


@app.post("/api/clear-cache", tags=["Partner Processing"])
async def clear_cache():
    """
    # Clear Partner Request Cache
    
    Deletes all cached partner matching results from the database.
    Use this when an Excel file was uploaded with incorrect column order,
    or when you need to force reprocessing of all partners with fresh data.
    
    ## Response
    ```json
    {
        "success": true,
        "cleared": 12,
        "message": "Cache cleared successfully. 12 entries removed."
    }
    ```
    
    ## HTTP Status Codes
    - **200**: Cache cleared successfully
    - **500**: Internal server error
    """
    try:
        cleared = clear_all_cache()
        return {
            "success": True,
            "cleared": cleared,
            "message": f"Cache cleared successfully. {cleared} entries removed."
        }
    except Exception as e:
        logger.error(f"❌ Error clearing cache via API: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")


@app.post("/api/process-partners", tags=["Partner Processing"])
async def process_partners(
    file: UploadFile = File(...),
    user_email: str = Form(...),
    user_name: str = Form(...),
    auth_token: str = Form(...),
    create_requests: bool = Form(default=True)
):
    """
    # Process Partner Requests from Excel File
    
    Processes an Excel file containing partner institution requests. The endpoint:
    1. Synchronizes the CLARISA institutions database
    2. Optionally creates partner requests in CLARISA
    3. Matches partners against the CLARISA database using AI-powered semantic search
    4. Performs web searches for additional validation when needed
    5. Caches results for performance optimization
    
    ## Excel File Format Requirements
    
    The uploaded file must be in `.xlsx` or `.xls` format with the following columns:
    
    | Column | Name | Required | Description |
    |--------|------|----------|-------------|
    | 0 | ID | Optional | Partner request identifier |
    | 1 | partner_name | **REQUIRED** | Full name of the partner institution |
    | 2 | acronym | Optional | Institution acronym or short name |
    | 3 | website | Optional | Official website URL |
    | 4 | institution_type | **REQUIRED** | Must match CLARISA control list |
    | 5 | country | **REQUIRED** | Must match CLARISA control list |
    | 6 | category_1 | Optional | Custom category field |
    | 7 | category_2 | Optional | Custom category field |
    
    ## Parameters
    
    - **file**: Excel file (multipart/form-data)
    - **user_email**: Email address of the requesting user
    - **user_name**: Full name of the requesting user
    - **auth_token**: Bearer token for CLARISA API authentication
    - **create_requests**: Whether to create partner requests in CLARISA before processing (default: true)
    
    ## Response Structure
    
    ```json
    {
        "partners": [
            {
                "id": "123",
                "partner_name": "Example University",
                "match_found": true,
                "match_quality": "excellent",
                "best_match": {...},
                "web_search": {...}
            }
        ],
        "stats": {
            "total": 10,
            "matched": 8,
            "no_match": 2,
            "excellent": 5,
            "good": 2,
            "fair": 1,
            "matched_percentage": 80.0
        },
        "creation_info": {
            "created": true,
            "found_existing": 3,
            "created_new": 7,
            "failed": 0
        },
        "cache_info": {
            "cache_hits": 2,
            "cache_misses": 8,
            "from_cache": true
        },
        "sync_info": {
            "sync_performed": true,
            "new_institutions": 5,
            "modified_institutions": 2,
            "sync_message": "Database updated successfully"
        }
    }
    ```
    
    ## Match Quality Levels
    
    - **excellent**: High confidence match (similarity > 0.85)
    - **good**: Probable match requiring review (0.75 - 0.85)
    - **fair**: Possible match requiring verification (0.65 - 0.75)
    - **no_match**: No suitable match found (< 0.65)
    
    ## HTTP Status Codes
    
    - **200**: Successfully processed the file
    - **400**: Invalid file format or missing required data
    - **500**: Internal server error during processing
    
    ## Notes
    
    - Country and Institution Type values are validated against CLARISA control lists
    - Invalid or missing required values will cause request creation to fail
    - Results are automatically cached by partner name for faster subsequent processing
    - Database synchronization happens automatically before processing
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an Excel file (.xlsx or .xls)"
        )

    temp_file = None
    try:
        try:
            check_supabase_connection()
        except ConnectionError as e:
            logger.error(f"❌ Supabase unreachable: {e}")
            raise HTTPException(
                status_code=503,
                detail=(
                    "Unable to connect to the database. Please check your internet "
                    "connection and try again, or contact support if the problem persists."
                )
            )

        logger.info("🔄 Synchronizing CLARISA institutions database...")
        institutions_before = count_institutions()
        sync_stats = sync_clarisa_institutions(batch_size=50, delete_obsolete=True)
        institutions_after = count_institutions()

        sync_info = {
            'sync_performed': True,
            'institutions_before': institutions_before,
            'institutions_after': institutions_after,
            'new_institutions': sync_stats['new'],
            'modified_institutions': sync_stats['modified'],
            'unchanged_institutions': sync_stats['unchanged'],
            'total_processed': sync_stats['new'] + sync_stats['modified'],
            'cache_cleared': sync_stats.get('cache_cleared', 0),
            'sync_message': None
        }

        if sync_stats['new'] > 0 or sync_stats['modified'] > 0:
            msg_parts = []
            if sync_stats['new'] > 0:
                msg_parts.append(f"{sync_stats['new']} new institution(s)")
            if sync_stats['modified'] > 0:
                msg_parts.append(f"{sync_stats['modified']} modified institution(s)")
            base_msg = f"Found {' and '.join(msg_parts)}. Database has been updated."
            if sync_stats.get('cache_cleared', 0) > 0:
                base_msg += f" Cache cleared ({sync_stats['cache_cleared']} entries) to ensure fresh matches."
            sync_info['sync_message'] = base_msg
            logger.info(f"✅ {sync_info['sync_message']}")
        else:
            sync_info['sync_message'] = "Database synchronized. No changes found in CLARISA."
            logger.info("✅ Database synchronized - no changes")

        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            contents = await file.read()
            temp_file.write(contents)
            temp_path = temp_file.name

        logger.info(f"📁 Processing file: {file.filename}")

        try:
            df = pd.read_excel(temp_path, engine='openpyxl')
            logger.info(f"✅ {len(df)} rows loaded from Excel")
        except Exception as e:
            logger.error(f"❌ Error reading Excel: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Error reading Excel file: {str(e)}"
            )

        if len(df.columns) < 2:
            raise HTTPException(
                status_code=400,
                detail="Excel file must have at least 2 columns (ID and partner_name)"
            )

        if df.iloc[:, 1].isna().all():
            raise HTTPException(
                status_code=400,
                detail="Partner name column (column 1) is empty"
            )

        creation_info = {
            'created': False,
            'total_attempts': 0,
            'found_existing': 0,
            'created_new': 0,
            'failed': 0,
            'existing_ids': [],
            'new_ids': []
        }

        if create_requests:
            logger.info("🔨 Processing partner requests creation in CLARISA API...")
            creation_info['created'] = True

            logger.info("🔍 Fetching existing pending partner requests...")
            existing_requests = []
            try:
                fetch_response = requests.get(
                    CLARISA_API_URL,
                    headers={"Authorization": f"Bearer {auth_token}"},
                    timeout=30
                )
                if fetch_response.status_code == 200:
                    existing_requests = fetch_response.json()
                    logger.info(f"📥 Fetched {len(existing_requests)} existing pending partner requests")
                else:
                    logger.warning(f"⚠️  Failed to fetch existing requests: {fetch_response.status_code}")
            except Exception as e:
                logger.error(f"❌ Error fetching existing requests: {e}")

            logger.info("🌍 Fetching countries control list...")
            countries_map = {}
            try:
                countries_response = requests.get(CLARISA_COUNTRIES_URL, timeout=30)
                if countries_response.status_code == 200:
                    for country in countries_response.json():
                        country_name = country.get('name', '').strip().lower()
                        iso_alpha2 = country.get('isoAlpha2', '')
                        if country_name and iso_alpha2:
                            countries_map[country_name] = iso_alpha2
                    logger.info(f"🌍 Loaded {len(countries_map)} countries for lookup")
                else:
                    logger.warning(f"⚠️  Failed to fetch countries list: {countries_response.status_code}")
            except Exception as e:
                logger.error(f"❌ Error fetching countries list: {e}")

            logger.info("🏢 Fetching institution types control list...")
            institution_types_map = {}
            try:
                institution_types_response = requests.get(CLARISA_INSTITUTION_TYPES_URL, timeout=30)
                if institution_types_response.status_code == 200:
                    for inst_type in institution_types_response.json():
                        type_name = inst_type.get('name', '').strip().lower()
                        type_code = inst_type.get('code')
                        if type_name and type_code is not None:
                            institution_types_map[type_name] = type_code
                    logger.info(f"🏢 Loaded {len(institution_types_map)} institution types for lookup")
                else:
                    logger.warning(f"⚠️  Failed to fetch institution types list: {institution_types_response.status_code}")
            except Exception as e:
                logger.error(f"❌ Error fetching institution types list: {e}")

            partners_to_create = []

            for idx, row in df.iterrows():
                creation_info['total_attempts'] += 1

                partner_name = row.iloc[1] if len(row) > 1 and pd.notna(row.iloc[1]) else None
                acronym = row.iloc[2] if len(row) > 2 and pd.notna(row.iloc[2]) else ""
                website = row.iloc[3] if len(row) > 3 and pd.notna(row.iloc[3]) else ""
                institution_type = row.iloc[4] if len(row) > 4 and pd.notna(row.iloc[4]) else ""
                country = row.iloc[5] if len(row) > 5 and pd.notna(row.iloc[5]) else ""
                category_1 = row.iloc[6] if len(row) > 6 and pd.notna(row.iloc[6]) else ""
                category_2 = row.iloc[7] if len(row) > 7 and pd.notna(row.iloc[7]) else ""

                if not partner_name:
                    logger.warning(f"⚠️  Skipping row {idx}: missing partner name")
                    creation_info['failed'] += 1
                    continue

                partner_name_lower = str(partner_name).strip().lower()
                existing_match = None
                for req in existing_requests:
                    existing_name = req.get('partnerName', '').strip().lower()
                    if existing_name == partner_name_lower:
                        existing_match = req
                        break

                if existing_match:
                    existing_id = existing_match.get('id')
                    if existing_id:
                        df.at[idx, df.columns[0]] = existing_id
                        creation_info['found_existing'] += 1
                        creation_info['existing_ids'].append(existing_id)
                        logger.info(f"✅ Found existing request {existing_id} for: {partner_name}")
                    else:
                        logger.warning(f"⚠️  Existing match has no ID for: {partner_name}")
                        creation_info['failed'] += 1
                else:
                    country_iso = None
                    if country and countries_map:
                        country_lower = str(country).strip().lower()
                        if country_lower in countries_map:
                            country_iso = countries_map[country_lower]
                            logger.info(f"🌍 Found country '{country}' -> {country_iso}")
                        else:
                            logger.warning(f"⚠️  Country '{country}' not found in control list. Skipping partner request creation.")
                    else:
                        logger.warning(f"⚠️  No country provided for '{partner_name}'. Skipping partner request creation.")

                    institution_type_code = None
                    if institution_type and institution_types_map:
                        institution_type_lower = str(institution_type).strip().lower()
                        if institution_type_lower in institution_types_map:
                            institution_type_code = institution_types_map[institution_type_lower]
                            logger.info(f"🏢 Found institution type '{institution_type}' -> {institution_type_code}")
                        else:
                            logger.warning(f"⚠️  Institution type '{institution_type}' not found in control list. Skipping partner request creation.")
                    else:
                        logger.warning(f"⚠️  No institution type provided for '{partner_name}'. Skipping partner request creation.")

                    if not country_iso or institution_type_code is None:
                        logger.error(f"❌ Cannot create partner request for '{partner_name}': missing required country or institution type")
                        creation_info['failed'] += 1
                        continue

                    payload = {
                        "name": str(partner_name),
                        "acronym": str(acronym) if acronym else "",
                        "websiteLink": str(website) if website else "",
                        "hqCountryIso": country_iso,
                        "institutionTypeCode": institution_type_code,
                        "category_1": str(category_1) if category_1 else "",
                        "category_2": str(category_2) if category_2 else "",
                        "externalUserMail": user_email,
                        "externalUserName": user_name,
                        "misAcronym": "CLARISA",
                        "externalUserComments": ""
                    }
                    partners_to_create.append({
                        'idx': idx,
                        'name': str(partner_name),
                        'acronym': str(acronym) if acronym else "",
                        'payload': payload
                    })

            if partners_to_create:
                logger.info(f"🔨 Creating {len(partners_to_create)} new partner requests...")
                for partner_info in partners_to_create:
                    try:
                        response = requests.post(
                            CLARISA_CREATE_URL,
                            json=partner_info['payload'],
                            headers={
                                "Authorization": f"Bearer {auth_token}",
                                "Content-Type": "application/json"
                            },
                            timeout=30
                        )
                        if response.status_code == 201 or response.status_code == 200:
                            creation_info['created_new'] += 1
                            logger.info(f"✅ Created new partner request for: {partner_info['name']}")
                        else:
                            logger.error(f"❌ Failed to create request for {partner_info['name']}: {response.status_code} - {response.text}")
                            creation_info['failed'] += 1
                    except Exception as e:
                        logger.error(f"❌ Error creating request for {partner_info['name']}: {e}")
                        creation_info['failed'] += 1

            newly_created_requests = []
            if creation_info['created_new'] > 0:
                logger.info("🔍 Fetching IDs for newly created partner requests...")
                try:
                    fetch_response = requests.get(
                        CLARISA_API_URL,
                        headers={"Authorization": f"Bearer {auth_token}"},
                        timeout=30
                    )
                    if fetch_response.status_code == 200:
                        all_requests = fetch_response.json()
                        logger.info(f"📥 Fetched {len(all_requests)} total partner requests")
                        for partner_info in partners_to_create:
                            partner_name_lower = partner_info['name'].strip().lower()
                            matching_requests = [
                                req for req in all_requests
                                if req.get('partnerName', '').strip().lower() == partner_name_lower
                            ]
                            if matching_requests:
                                matched_request = matching_requests[-1]
                                request_id = matched_request.get('id')
                                if request_id:
                                    df.at[partner_info['idx'], df.columns[0]] = request_id
                                    creation_info['new_ids'].append(request_id)
                                    newly_created_requests.append(matched_request)
                                    logger.info(f"✅ Matched ID {request_id} to: {partner_info['name']}")
                                else:
                                    logger.warning(f"⚠️  No ID found for: {partner_info['name']}")
                            else:
                                logger.warning(f"⚠️  Could not find created request for: {partner_info['name']}")
                        logger.info(f"✅ Retrieved {len(creation_info['new_ids'])} IDs for newly created requests")
                        if newly_created_requests:
                            synced_partner_requests.extend(newly_created_requests)
                            logger.info(f"📋 Added {len(newly_created_requests)} new requests to synced list")
                    else:
                        logger.error(f"❌ Failed to fetch partner requests: {fetch_response.status_code}")
                except Exception as e:
                    logger.error(f"❌ Error fetching partner requests: {e}")

            if creation_info['existing_ids']:
                existing_to_add = []
                for req in existing_requests:
                    if req.get('id') in creation_info['existing_ids']:
                        if not any(s.get('id') == req.get('id') for s in synced_partner_requests):
                            existing_to_add.append(req)
                if existing_to_add:
                    synced_partner_requests.extend(existing_to_add)
                    logger.info(f"📋 Added {len(existing_to_add)} existing requests to synced list")

            logger.info(f"📊 Summary: {creation_info['found_existing']} existing found, {creation_info['created_new']} newly created, {creation_info['failed']} failed")

        partner_names = []
        for idx, row in df.iterrows():
            partner_name = row.iloc[1] if len(row) > 1 and pd.notna(row.iloc[1]) else None
            if partner_name:
                partner_names.append(str(partner_name))

        cached_results_by_name = {}
        cache_info = {
            'total_requests': len(df),
            'cache_hits': 0,
            'cache_misses': len(df),
            'from_cache': False,
            'processed_new': False
        }

        if partner_names:
            logger.info(f"🔍 Checking cache by name for {len(partner_names)} partners...")
            cached_results_by_name = get_cached_results_by_name(partner_names)
            cache_info['cache_hits'] = len(cached_results_by_name)
            cache_info['cache_misses'] = len(partner_names) - len(cached_results_by_name)
            cache_info['from_cache'] = len(cached_results_by_name) > 0
            logger.info(f"📦 Cache status: {cache_info['cache_hits']} hits, {cache_info['cache_misses']} misses")

        cached_partners = []
        newly_processed_partners = []
        processing_stats = {
            'total': 0,
            'matched': 0,
            'no_match': 0,
            'web_search_attempted': 0,
            'web_search_success': 0,
            'errors': 0,
            'excellent': 0,
            'good': 0,
            'fair': 0
        }

        if cached_results_by_name:
            cached_names_lower = set(cached_results_by_name.keys())
            rows_to_process = []
            for idx, row in df.iterrows():
                partner_name = row.iloc[1] if len(row) > 1 and pd.notna(row.iloc[1]) else None
                if partner_name:
                    name_lower = str(partner_name).strip().lower()
                    if name_lower in cached_names_lower:
                        cached_result = cached_results_by_name[name_lower].copy()
                        current_request_id = row.iloc[0] if len(row) > 0 and pd.notna(row.iloc[0]) else None
                        if current_request_id:
                            try:
                                cached_result['id'] = str(int(current_request_id))
                                if cached_result.get('api_data'):
                                    cached_result['api_data']['request_id'] = int(current_request_id)
                            except (ValueError, TypeError):
                                pass
                        cached_partners.append(cached_result)
                    else:
                        rows_to_process.append(idx)
                else:
                    rows_to_process.append(idx)

            if rows_to_process:
                df_to_process = df.loc[rows_to_process].copy()
                cache_info['processed_new'] = True
            else:
                df_to_process = pd.DataFrame()
                logger.info("✨ All partners found in cache - no processing needed")
        else:
            df_to_process = df
            cache_info['processed_new'] = True

        if not df_to_process.empty:
            logger.info(f"🚀 Processing {len(df_to_process)} new partners...")
            processing_results = process_partners_to_json(df_to_process)
            processing_stats = processing_results['stats']
            newly_processed_partners = processing_results['partners']

            for i, partner_result in enumerate(newly_processed_partners):
                row_idx = df_to_process.index[i]
                request_id = df_to_process.loc[row_idx].iloc[0] if pd.notna(df_to_process.loc[row_idx].iloc[0]) else None
                if request_id:
                    try:
                        partner_result['api_data'] = {
                            'request_id': int(request_id),
                            'request_source': 'excel_upload',
                            'external_user': user_name,
                            'created_at': None
                        }
                    except (ValueError, TypeError):
                        pass

            if newly_processed_partners:
                cache_stats = cache_results_batch(newly_processed_partners)
                logger.info(f"💾 Cached {cache_stats['cached']} new results")
        else:
            logger.info("✨ All partners found in cache - no processing needed")

        all_partners = cached_partners + newly_processed_partners

        if cached_partners:
            for partner in cached_partners:
                processing_stats['total'] += 1
                if partner.get('match_found'):
                    processing_stats['matched'] += 1
                    quality = partner.get('match_quality', 'no_match')
                    if quality == 'excellent':
                        processing_stats['excellent'] += 1
                    elif quality == 'good':
                        processing_stats['good'] += 1
                    elif quality == 'fair':
                        processing_stats['fair'] += 1
                else:
                    processing_stats['no_match'] += 1
                if partner.get('web_search'):
                    processing_stats['web_search_attempted'] += 1
                    if partner['web_search'].get('success'):
                        processing_stats['web_search_success'] += 1

        if processing_stats['total'] > 0:
            processing_stats['matched_percentage'] = round(
                processing_stats['matched'] / processing_stats['total'] * 100, 1
            )
            processing_stats['no_match_percentage'] = round(
                processing_stats['no_match'] / processing_stats['total'] * 100, 1
            )

        results = {
            'partners': all_partners,
            'stats': processing_stats,
            'creation_info': creation_info,
            'cache_info': cache_info,
            'sync_info': sync_info
        }

        logger.info("✅ Processing completed successfully")
        return JSONResponse(content=results)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error processing file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )
    finally:
        if temp_file and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
                logger.info("🗑️  Temporary file cleaned up")
            except Exception as e:
                logger.warning(f"⚠️  Could not delete temporary file: {e}")



@app.get("/api/sync-partner-requests", tags=["Synchronization"])
async def sync_partner_requests():
    """
    # Synchronize Partner Requests from CLARISA
    
    Fetches all pending partner requests from the external CLARISA API and stores them
    in memory for processing. This endpoint should be called before using the
    `/api/process-api-partners` endpoint.
    
    ## Response Structure
    
    ```json
    {
        "success": true,
        "count": 25,
        "total_requests": 100,
        "pending_requests": [
            {
                "id": 123,
                "partnerName": "Example University",
                "acronym": "EU",
                "webPage": "https://example.edu",
                "requestStatus": "Pending",
                "countryDTO": {"name": "United States"},
                "institutionTypeDTO": {"name": "University"}
            }
        ]
    }
    ```
    
    ## Response Fields
    
    - **success**: Boolean indicating operation success
    - **count**: Number of pending partner requests
    - **total_requests**: Total number of all requests (any status)
    - **pending_requests**: Array of pending partner request objects
    
    ## HTTP Status Codes
    
    - **200**: Successfully synchronized partner requests
    - **502**: Error connecting to CLARISA API
    - **500**: Internal server error
    
    ## Notes
    
    - Only requests with status "Pending" are returned
    - Results are stored in server memory for subsequent processing
    - This is a read-only operation that doesn't modify any data
    """
    global synced_partner_requests
    
    try:
        logger.info(f"🔄 Fetching partner requests from {CLARISA_API_URL}")
        
        response = requests.get(CLARISA_API_URL, timeout=30)
        response.raise_for_status()
        
        partner_requests = response.json()
        
        pending_requests = [
            pr for pr in partner_requests 
            if pr.get('requestStatus') == 'Pending'
        ]
        
        synced_partner_requests = pending_requests
        
        logger.info(f"✅ Synced {len(pending_requests)} pending partner requests")
        
        return {
            "success": True,
            "count": len(pending_requests),
            "total_requests": len(partner_requests),
            "pending_requests": pending_requests
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error fetching partner requests: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Error connecting to CLARISA API: {str(e)}"
        )
    except Exception as e:
        logger.error(f"❌ Error processing partner requests: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing partner requests: {str(e)}"
        )


@app.post("/api/sync-clarisa-institutions", tags=["Synchronization"])
async def sync_clarisa_institutions_endpoint(delete_obsolete: bool = Body(True)):
    """
    # Synchronize CLARISA Institutions Database
    
    Manually triggers a complete synchronization of the local institutions database with
    the CLARISA API. This operation:
    - Fetches all institutions from CLARISA
    - Compares with local database to identify changes
    - Adds new institutions with AI-generated embeddings
    - Updates modified institutions
    - Optionally removes obsolete institutions
    - Clears cache when changes are detected
    
    ## Request Body
    
    ```json
    {
        "delete_obsolete": true
    }
    ```
    
    ## Parameters
    
    - **delete_obsolete**: Whether to delete institutions that no longer exist in CLARISA (default: true)
    
    ## Response Structure
    
    ```json
    {
        "success": true,
        "institutions_before": 1500,
        "institutions_after": 1520,
        "new_institutions": 25,
        "modified_institutions": 10,
        "unchanged_institutions": 1465,
        "obsolete_institutions": 5,
        "deleted_institutions": 5,
        "cache_cleared": 15,
        "total_processed": 35,
        "message": "Sync completed: 25 new institution(s) added, 10 institution(s) updated, 5 obsolete institution(s) deleted."
    }
    ```
    
    ## Response Fields
    
    - **success**: Operation completion status
    - **institutions_before**: Database count before synchronization
    - **institutions_after**: Database count after synchronization
    - **new_institutions**: Number of newly added institutions
    - **modified_institutions**: Number of updated institutions
    - **unchanged_institutions**: Number of institutions without changes
    - **obsolete_institutions**: Number of obsolete institutions detected
    - **deleted_institutions**: Number of institutions removed (if delete_obsolete=true)
    - **cache_cleared**: Number of cache entries cleared
    - **total_processed**: Total institutions requiring embedding generation
    - **message**: Human-readable summary of the sync operation
    
    ## HTTP Status Codes
    
    - **200**: Synchronization completed successfully
    - **500**: Error during synchronization process
    
    ## Notes
    
    - This operation automatically happens during `/api/process-partners` but can be triggered manually
    - Embeddings are generated only for new or modified institutions
    - Cache is automatically cleared when institutions are added or modified
    - The operation is idempotent and safe to call multiple times
    - Processing time depends on the number of new/modified institutions
    """
    try:
        logger.info("🔄 Manual CLARISA institutions sync triggered")
        
        institutions_before = count_institutions()
        logger.info(f"📊 Institutions before sync: {institutions_before}")
        
        sync_stats = sync_clarisa_institutions(batch_size=50, delete_obsolete=delete_obsolete)
        
        institutions_after = count_institutions()
        logger.info(f"📊 Institutions after sync: {institutions_after}")
        
        message_parts = []
        if sync_stats['new'] > 0:
            message_parts.append(f"{sync_stats['new']} new institution(s) added")
        if sync_stats['modified'] > 0:
            message_parts.append(f"{sync_stats['modified']} institution(s) updated")
        if sync_stats['unchanged'] > 0:
            message_parts.append(f"{sync_stats['unchanged']} unchanged")
        if sync_stats['obsolete'] > 0:
            if delete_obsolete:
                message_parts.append(f"{sync_stats['deleted']} obsolete institution(s) deleted")
            else:
                message_parts.append(f"{sync_stats['obsolete']} obsolete institution(s) found")
        
        if sync_stats.get('cache_cleared', 0) > 0:
            message_parts.append(f"{sync_stats['cache_cleared']} cache entries cleared")
        
        if message_parts:
            message = "Sync completed: " + ", ".join(message_parts) + "."
        else:
            message = "Database synchronized. No changes found."
        
        result = {
            'success': True,
            'institutions_before': institutions_before,
            'institutions_after': institutions_after,
            'new_institutions': sync_stats['new'],
            'modified_institutions': sync_stats['modified'],
            'unchanged_institutions': sync_stats['unchanged'],
            'obsolete_institutions': sync_stats['obsolete'],
            'deleted_institutions': sync_stats.get('deleted', 0),
            'cache_cleared': sync_stats.get('cache_cleared', 0),
            'total_processed': sync_stats['new'] + sync_stats['modified'],
            'message': message
        }
        
        logger.info(f"✅ Sync completed: {message}")
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"❌ Error during manual sync: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error syncing CLARISA institutions: {str(e)}"
        )


@app.post("/api/process-api-partners", tags=["Partner Processing"])
async def process_api_partners(partner_ids: Optional[List[int]] = Body(None)):
    """
    # Process Partner Requests from Synced API Data
    
    Processes partner requests that were previously synchronized from the CLARISA API
    using the `/api/sync-partner-requests` endpoint. This endpoint performs intelligent
    matching against the CLARISA institutions database with caching support.
    
    ## Prerequisites
    
    Call `/api/sync-partner-requests` first to load partner requests into memory.
    
    ## Request Body
    
    ```json
    {
        "partner_ids": [123, 456, 789]
    }
    ```
    
    ## Parameters
    
    - **partner_ids**: Optional array of specific partner request IDs to process
      - If provided: processes only the specified IDs
      - If null/omitted: processes last 5 synced partners (for testing)
    
    ## Response Structure
    
    ```json
    {
        "partners": [
            {
                "id": "123",
                "partner_name": "Example Research Institute",
                "match_found": true,
                "match_quality": "excellent",
                "similarity_score": 0.92,
                "best_match": {
                    "id": 456,
                    "name": "Example Research Institute",
                    "acronym": "ERI",
                    "websiteLink": "https://eri.org"
                },
                "api_data": {
                    "request_id": 123,
                    "request_source": "External",
                    "external_user": "John Doe"
                },
                "web_search": {
                    "success": true,
                    "formatted_result": "..."
                }
            }
        ],
        "stats": {
            "total": 5,
            "matched": 4,
            "no_match": 1,
            "excellent": 3,
            "good": 1,
            "fair": 0,
            "web_search_attempted": 1,
            "web_search_success": 1,
            "matched_percentage": 80.0
        },
        "cache_info": {
            "total_requests": 5,
            "cache_hits": 2,
            "cache_misses": 3,
            "from_cache": true,
            "processed_new": true
        },
        "sync_info": {
            "sync_performed": true,
            "institutions_after": 1520,
            "new_institutions": 0,
            "sync_message": "Database synchronized. No changes found."
        }
    }
    ```
    
    ## HTTP Status Codes
    
    - **200**: Successfully processed partner requests
    - **400**: No partner requests in memory (sync required)
    - **404**: Specified partner IDs not found
    - **500**: Internal server error
    
    ## Performance Features
    
    - **Smart Caching**: Previously processed partners are retrieved from cache
    - **Batch Processing**: Efficient handling of multiple requests
    - **Auto-Sync**: Automatically synchronizes institutions database before processing
    
    ## Notes
    
    - Processes only pending partner requests
    - Results include API metadata (request_id, source, user)
    - Cache is based on partner name (case-insensitive)
    - Newly processed results are automatically cached
    """
    global synced_partner_requests
    
    if not synced_partner_requests:
        raise HTTPException(
            status_code=400,
            detail="No partner requests available. Please sync first using /api/sync-partner-requests"
        )
    
    try:
        logger.info("🔄 Synchronizing CLARISA institutions database...")
        institutions_before = count_institutions()
        sync_stats = sync_clarisa_institutions(batch_size=50, delete_obsolete=True)
        institutions_after = count_institutions()
        
        sync_info = {
            'sync_performed': True,
            'institutions_before': institutions_before,
            'institutions_after': institutions_after,
            'new_institutions': sync_stats['new'],
            'modified_institutions': sync_stats['modified'],
            'unchanged_institutions': sync_stats['unchanged'],
            'total_processed': sync_stats['new'] + sync_stats['modified'],
            'cache_cleared': sync_stats.get('cache_cleared', 0),
            'sync_message': None
        }
        
        if sync_stats['new'] > 0 or sync_stats['modified'] > 0:
            msg_parts = []
            if sync_stats['new'] > 0:
                msg_parts.append(f"{sync_stats['new']} new institution(s)")
            if sync_stats['modified'] > 0:
                msg_parts.append(f"{sync_stats['modified']} modified institution(s)")
            
            base_msg = f"Found {' and '.join(msg_parts)}. Database has been updated."
            
            if sync_stats.get('cache_cleared', 0) > 0:
                base_msg += f" Cache cleared ({sync_stats['cache_cleared']} entries) to ensure fresh matches."
            
            sync_info['sync_message'] = base_msg
            logger.info(f"✅ {sync_info['sync_message']}")
        else:
            sync_info['sync_message'] = "Database synchronized. No changes found in CLARISA."
            logger.info("✅ Database synchronized - no changes")
        
        if partner_ids:
            partners_to_process = [
                pr for pr in synced_partner_requests 
                if pr.get('id') in partner_ids
            ]
        else:
            partners_to_process = synced_partner_requests
        
        if not partners_to_process:
            raise HTTPException(
                status_code=404,
                detail="No matching partner requests found"
            )
        
        logger.info(f"🚀 Processing {len(partners_to_process)} partner requests from API")
        
        partner_names = [pr.get('partnerName') for pr in partners_to_process if pr.get('partnerName')]
        cached_results_by_name = get_cached_results_by_name(partner_names)
        
        cached_partners = []
        partners_to_compute = []
        
        for pr in partners_to_process:
            partner_name = pr.get('partnerName', '').strip().lower()
            
            if partner_name in cached_results_by_name:
                cached_result = cached_results_by_name[partner_name].copy()
                
                current_id = pr.get('id')
                if current_id:
                    cached_result['id'] = str(current_id)
                    if cached_result.get('api_data'):
                        cached_result['api_data']['request_id'] = current_id
                
                cached_partners.append(cached_result)
            else:
                partners_to_compute.append(pr)
        
        cache_info = {
            'total_requests': len(partners_to_process),
            'cache_hits': len(cached_partners),
            'cache_misses': len(partners_to_compute),
            'from_cache': len(cached_partners) > 0,
            'processed_new': len(partners_to_compute) > 0
        }
        
        logger.info(f"📦 Cache status: {cache_info['cache_hits']} hits, {cache_info['cache_misses']} misses")
        
        newly_processed_partners = []
        processing_stats = {
            'total': 0,
            'matched': 0,
            'no_match': 0,
            'web_search_attempted': 0,
            'web_search_success': 0,
            'errors': 0,
            'excellent': 0,
            'good': 0,
            'fair': 0
        }
        
        if partners_to_compute:
            logger.info(f"🔄 Processing {len(partners_to_compute)} new partner requests")
            
            data_rows = []
            for pr in partners_to_compute:
                row = {
                    'id': pr.get('id', ''),
                    'partner_name': pr.get('partnerName', ''),
                    'acronym': pr.get('acronym', ''),
                    'website': pr.get('webPage', ''),
                    'country': pr.get('countryDTO', {}).get('name', ''),
                    'institution_type': pr.get('institutionTypeDTO', {}).get('name', ''),
                    'request_source': pr.get('requestSource', ''),
                    'external_user': pr.get('externalUserName', ''),
                }
                data_rows.append(row)
            
            df = pd.DataFrame(data_rows)
            
            df_ordered = pd.DataFrame({
                'id': df['id'],
                'partner_name': df['partner_name'],
                'acronym': df['acronym'],
                'website': df['website'],
                'placeholder': '',  # Column 4 placeholder
                'country': df['country'],
            })
            
            logger.info(f"📊 Created DataFrame with {len(df_ordered)} rows")
            
            processing_results = process_partners_to_json(df_ordered)
            processing_stats = processing_results['stats']
            
            for i, partner_result in enumerate(processing_results['partners']):
                if i < len(partners_to_compute):
                    partner_result['api_data'] = {
                        'request_id': partners_to_compute[i].get('id'),
                        'request_source': partners_to_compute[i].get('requestSource'),
                        'external_user': partners_to_compute[i].get('externalUserName'),
                        'created_at': partners_to_compute[i].get('created_at'),
                    }
            
            newly_processed_partners = processing_results['partners']
            
            cache_stats = cache_results_batch(newly_processed_partners)
            logger.info(f"💾 Cached {cache_stats['cached']} new results")
        else:
            logger.info("✨ All requests found in cache - no processing needed")
        
        all_partners = cached_partners + newly_processed_partners
        
        if cached_partners:
            for partner in cached_partners:
                processing_stats['total'] += 1
                if partner.get('match_found'):
                    processing_stats['matched'] += 1
                    quality = partner.get('match_quality', 'no_match')
                    if quality == 'excellent':
                        processing_stats['excellent'] += 1
                    elif quality == 'good':
                        processing_stats['good'] += 1
                    elif quality == 'fair':
                        processing_stats['fair'] += 1
                else:
                    processing_stats['no_match'] += 1
                
                if partner.get('web_search'):
                    processing_stats['web_search_attempted'] += 1
                    if partner['web_search'].get('success'):
                        processing_stats['web_search_success'] += 1
        
        if processing_stats['total'] > 0:
            processing_stats['matched_percentage'] = round(
                processing_stats['matched'] / processing_stats['total'] * 100, 1
            )
            processing_stats['no_match_percentage'] = round(
                processing_stats['no_match'] / processing_stats['total'] * 100, 1
            )
        
        results = {
            'partners': all_partners,
            'stats': processing_stats,
            'cache_info': cache_info,
            'sync_info': sync_info
        }
        
        logger.info("✅ API partners processing completed successfully")
        
        return JSONResponse(content=results)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error processing API partners: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing API partners: {str(e)}"
        )


@app.post("/api/respond-partner-request", tags=["Partner Processing"])
async def respond_partner_request(
    request_id: int = Body(...),
    user_id: int = Body(...),
    accept: bool = Body(...),
    auth_token: str = Body(...),
    reject_justification: Optional[str] = Body(None)
):
    """
    # Accept or Reject a Partner Request
    
    Submits a decision (accept/reject) for a partner request to the CLARISA API.
    Upon successful submission, the request is removed from the local synced list.
    
    ## Request Body
    
    ```json
    {
        "request_id": 123,
        "user_id": 456,
        "accept": true,
        "auth_token": "Bearer eyJ...",
        "reject_justification": "Does not meet criteria"
    }
    ```
    
    ## Parameters
    
    - **request_id**: ID of the partner request to respond to (required)
    - **user_id**: ID of the authenticated CLARISA user making the decision (required)
    - **accept**: Boolean decision - true to accept, false to reject (required)
    - **auth_token**: Bearer authentication token for CLARISA API (required)
    - **reject_justification**: Explanation text required when rejecting (optional for accept, recommended for reject)
    
    ## Response Structure
    
    ### Success Response
    ```json
    {
        "success": true,
        "action": "accept",
        "request_id": 123,
        "message": "Partner request successfully accepted"
    }
    ```
    
    ### Error Response
    ```json
    {
        "detail": "Error message describing what went wrong"
    }
    ```
    
    ## Response Fields
    
    - **success**: Boolean indicating operation success
    - **action**: The action performed ("accept" or "reject")
    - **request_id**: ID of the processed request
    - **message**: Human-readable confirmation message
    
    ## HTTP Status Codes
    
    - **200**: Request successfully accepted or rejected
    - **404**: Partner request not found in synced list
    - **401/403**: Authentication or authorization error
    - **502**: Network error connecting to CLARISA API
    - **500**: Internal server error
    
    ## Workflow
    
    1. Validates request exists in local synced list
    2. Constructs payload with request data and user information
    3. Sends decision to CLARISA API
    4. Removes request from local synced list on success
    
    ## Notes
    
    - Partner request metadata is fetched live from CLARISA at the time of the call
    - Rejection requires justification text (auto-filled if not provided)
    - This operation is final and cannot be undone
    - Authentication token must have appropriate CLARISA permissions
    """
    try:
        logger.info(f"🔍 Fetching partner request {request_id} from CLARISA API...")
        try:
            fetch_response = requests.get(
                CLARISA_API_URL,
                headers={"Authorization": f"Bearer {auth_token}"},
                timeout=30
            )
            fetch_response.raise_for_status()
            all_requests = fetch_response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to fetch partner requests from CLARISA: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Error fetching partner request from CLARISA API: {str(e)}"
            )

        partner_request = next(
            (pr for pr in all_requests if pr.get('id') == request_id),
            None
        )

        if not partner_request:
            raise HTTPException(
                status_code=404,
                detail=f"Partner request {request_id} not found in CLARISA."
            )

        payload = {
            "requestId": request_id,
            "userId": user_id,
            "accept": accept,
            "misAcronym": partner_request.get('mis', 'CLARISA'),
            "externalUserMail": partner_request.get('externalUserMail', ''),
            "externalUserName": partner_request.get('externalUserName', ''),
            "externalUserComments": partner_request.get('externalUserComments', '')
        }
        
        if not accept:
            payload["rejectJustification"] = reject_justification or "No justification provided"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}"
        }
        
        action = "accept" if accept else "reject"
        logger.info(f"📤 Sending {action} request for partner {request_id} to CLARISA API")
        
        response = requests.post(
            CLARISA_RESPOND_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        response.raise_for_status()
        
        logger.info(f"✅ Successfully {action}ed partner request {request_id}")

        return {
            "success": True,
            "action": action,
            "request_id": request_id,
            "message": f"Partner request successfully {action}ed"
        }
        
    except requests.exceptions.HTTPError as e:
        error_detail = "Unknown error"
        try:
            error_detail = e.response.json() if e.response else str(e)
        except:
            error_detail = str(e)
        
        logger.error(f"❌ HTTP Error responding to partner request {request_id}: {error_detail}")
        raise HTTPException(
            status_code=e.response.status_code if e.response else 500,
            detail=f"Error responding to partner request: {error_detail}"
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Network error responding to partner request {request_id}: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Network error connecting to CLARISA API: {str(e)}"
        )
    except Exception as e:
        logger.error(f"❌ Error responding to partner request {request_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing response: {str(e)}"
        )


@app.post("/api/manual-web-search", tags=["Web Search"])
async def manual_web_search(
    partner_name: str = Body(...),
    country: Optional[str] = Body(None),
    website: Optional[str] = Body(None)
):
    """
    # Manual Web Search for Partner Institution
    
    Performs an AI-powered web search to gather additional information about a partner
    institution. Particularly useful when match quality is 'fair' or 'good' and manual
    verification is needed.
    
    ## Use Cases
    
    - Verify questionable matches before accepting
    - Gather additional context for decision-making
    - Validate institution details when database match is uncertain
    - Research institutions with incomplete information
    
    ## Request Body
    
    ```json
    {
        "partner_name": "MIT",
        "country": "United States",
        "website": "https://mit.edu"
    }
    ```
    
    ## Parameters
    
    - **partner_name**: Full or partial name of the institution (required)
    - **country**: Country where the institution is located (optional, improves accuracy)
    - **website**: Official website URL (optional, helps verify identity)
    
    ## Response Structure
    
    ### Success Response
    ```json
    {
        "success": true,
        "result": "Massachusetts Institute of Technology (MIT) is a private research university located in Cambridge, Massachusetts, United States. Founded in 1861, it is known for..."
    }
    ```
    
    ### Failure Response
    ```json
    {
        "success": false,
        "error": "No relevant information found"
    }
    ```
    
    ## Response Fields
    
    - **success**: Boolean indicating if search succeeded
    - **result**: Formatted text with institution information (on success)
    - **error**: Error message explaining failure (on failure)
    
    ## HTTP Status Codes
    
    - **200**: Search completed (check 'success' field for outcome)
    - **500**: Internal server error during search
    
    ## Search Features
    
    - **AI-Powered**: Uses Bedrock AI to analyze and summarize web results
    - **Multi-Source**: Searches across multiple web sources
    - **Contextual**: Considers country and website for better relevance
    - **Formatted Output**: Returns clean, readable summaries
    
    ## Notes
    
    - Search results are not cached
    - Response time varies (typically 3-10 seconds)
    - Quality depends on available online information
    - Results are AI-generated summaries, not raw search results
    """
    try:
        logger.info(f"🔍 Manual web search triggered for: {partner_name}")
        
        web_result = search_institution_online(partner_name, country, website)
        
        if web_result['success']:
            logger.info(f"✅ Manual web search successful for: {partner_name}")
            return {
                "success": True,
                "result": web_result.get('formatted_result', '')
            }
        else:
            logger.warning(f"⚠️ Manual web search failed for: {partner_name}")
            return {
                "success": False,
                "error": web_result.get('error', 'Unknown error')
            }
            
    except Exception as e:
        logger.error(f"❌ Error in manual web search: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error performing web search: {str(e)}"
        )


@app.get("/api/download-template", tags=["Templates"])
async def download_template():
    """
    # Download Excel Template
    
    Downloads the official Excel template file for partner request submissions from AWS S3.
    This template includes the correct column structure, headers, and formatting required
    for the `/api/process-partners` endpoint.
    
    ## Response
    
    Returns an Excel file (.xlsx) as a downloadable attachment.
    
    **Filename**: `PartnerRequestTemplate_v1.xlsx`
    
    ## Template Structure
    
    The template includes the following columns:
    
    | Column | Header | Description |
    |--------|--------|-------------|
    | A | ID | Optional request identifier |
    | B | Partner Name* | Institution name (required) |
    | C | Acronym | Short name or abbreviation |
    | D | Website | Official website URL |
    | E | Institution Type* | Must match CLARISA list (required) |
    | F | Country* | Must match CLARISA list (required) |
    | G | Category 1 | Custom category field |
    | H | Category 2 | Custom category field |
    
    *Required fields
    
    ## HTTP Status Codes
    
    - **200**: Template file successfully downloaded
    - **404**: Template bucket or file not found in S3
    - **500**: Error accessing S3 or downloading file
    
    ## Configuration
    
    Template location is configured via environment variables:
    - `S3_TEMPLATE_BUCKET`: S3 bucket name (default: "cgiar-partner-templates")
    - `S3_TEMPLATE_KEY`: File key/path (default: "PartnerRequestTemplate_v1.xlsx")
    
    ## Notes
    
    - Uses the same AWS credentials as Bedrock AI service
    - File is streamed directly from S3 (not stored locally)
    - Template includes data validation for required fields
    - Always use the latest template version for best compatibility
    """
    try:
        bucket_name = os.getenv("S3_TEMPLATE_BUCKET", "cgiar-partner-templates")
        template_key = os.getenv("S3_TEMPLATE_KEY", "PartnerRequestTemplate_v1.xlsx")

        s3_client = boto3.client(
            's3',
            aws_access_key_id=BR['aws_access_key'],
            aws_secret_access_key=BR['aws_secret_key'],
            region_name='us-east-1'
        )
        
        logger.info(f"📥 Downloading template from S3: {bucket_name}/{template_key}")
        
        file_obj = io.BytesIO()
        s3_client.download_fileobj(bucket_name, template_key, file_obj)
        file_obj.seek(0)
        
        logger.info("✅ Template downloaded successfully")
        
        return StreamingResponse(
            file_obj,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=PartnerRequestTemplate_v1.xlsx"
            }
        )
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            logger.error(f"❌ S3 bucket not found: {bucket_name}")
            raise HTTPException(
                status_code=404,
                detail=f"Template bucket not found. Please contact administrator."
            )
        elif error_code == 'NoSuchKey' or error_code == '404':
            logger.error(f"❌ Template file not found in S3: {template_key}")
            raise HTTPException(
                status_code=404,
                detail=f"Template file not found. Please contact administrator."
            )
        else:
            logger.error(f"❌ AWS error downloading template: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error downloading template: {str(e)}"
            )
    except Exception as e:
        logger.error(f"❌ Error downloading template from S3: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error downloading template: {str(e)}"
        )




# ============================================================================
# AUTOMATED PARTNER REQUEST PROCESSING ENDPOINT
# ============================================================================

@app.post("/api/auto-partner-request", tags=["Automated Processing"], response_model=AutoPartnerResponse)
async def auto_partner_request(body: AutoPartnerRequest):
    """
    # Automated Partner Request Evaluation

    Fully automated evaluation of a single partner institution request.
    Runs the complete pipeline — CLARISA hybrid search + AI web search — and
    returns a standardized **ACCEPT / REJECT** decision without any human
    intervention.

    This endpoint is designed for external platforms that need to automate the
    partner approval workflow. It reuses all existing matching and search
    components but is completely independent from the manual review frontend.

    ## Decision Logic

    | CLARISA match quality | Duplicate check | Web search + rules | Decision |
    |---|---|---|---|
    | Excellent (> 0.95) | No | No | REJECT (near-certain duplicate, no further checks) |
    | Very Good (0.85 – 0.95) | Yes — small/fast model | If not confirmed as duplicate | REJECT (confirmed duplicate) or fall through |
    | Good (0.70 – 0.85) | Yes — small/fast model | If not confirmed as duplicate | REJECT (confirmed duplicate) or fall through |
    | Fair (0.60 – 0.70) | No (skipped — score too low) | Yes | ACCEPT or MANUAL_REVIEW |
    | No match (< 0.60) | No (skipped) | Yes | ACCEPT or MANUAL_REVIEW |

    Two-step AI logic:
    1. **Duplicate check** (Very Good / Good only): a smaller/faster model compares the
       requester's submitted metadata against the CLARISA candidate. If confirmed as the
       same institution → REJECT. Otherwise, falls through to step 2 (this is NOT itself
       a rejection).
    2. **Rules validation** (Fair, No match, and Very Good/Good falling through from
       step 1): a web search + larger model evaluates CGIAR eligibility criteria (legal
       entity status, institution type, research mandate). If the rules validation
       passes → ACCEPT. Otherwise → **MANUAL_REVIEW** (not a rejection — the AI was
       not confident enough to auto-approve, so a human makes the final call). This
       decision is based solely on the rules validation outcome — a request with every
       field filled in gets the exact same review as one with missing fields; field
       completeness (`fields_complete`/`missing_fields` in the response) is tracked only
       as informational metadata for whoever ends up handling the manual review, and
       never gates ACCEPT on its own.

    `decision` is one of `"ACCEPT"`, `"REJECT"`, or `"MANUAL_REVIEW"`. ACCEPT/REJECT
    are submitted to CLARISA's own respond endpoint (which already notifies the
    requester, same as the manual flow). Only `MANUAL_REVIEW` triggers a notification
    from this service (see `backend/src/notifications.py`) — it makes no CLARISA call
    at all (the request is left in `Pending` status for the existing manual
    `/api/respond-partner-request` endpoint), so without it the case would otherwise
    go silent. That notification goes to both the requester and the PRMS admin, and
    carries a mandatory AI disclaimer.

    ## Request Body

    ```json
    {
        "partner_name": "University of Nairobi",
        "country": "Kenya",
        "website": "https://www.uonbi.ac.ke",
        "acronym": "UoN",
        "institution_type": "University",
        "create_in_clarisa": true,
        "external_user_mail": "requester@cgiar.org",
        "external_user_name": "Jane Doe",
        "external_user_comments": "Needed for project INIT-2024",
        "mis_acronym": "CLARISA",
        "auth_token": "Bearer eyJ...",
        "user_id": 456,
        "auto_respond": true,
        "request_id": null
    }
    ```

    ## Parameters

    - **partner_name** *(required)*: Full institution name
    - **country** *(optional)*: Country name — improves search accuracy. Required when `create_in_clarisa=true`
    - **website** *(optional)*: Official website — enables focused domain search
    - **acronym** *(optional)*: Institution acronym — improves CLARISA matching
    - **institution_type** *(optional)*: Declared institution type. Required when `create_in_clarisa=true`
    - **create_in_clarisa** *(optional, default false)*: If `true`, creates the partner request in CLARISA first,
      then analyzes and auto-responds. Requires `country`, `institution_type`, `auth_token`, `user_id`,
      `external_user_mail`, and `external_user_name`
    - **external_user_mail** *(optional)*: Email of the user requesting the partnership. Required when `create_in_clarisa=true`
    - **external_user_name** *(optional)*: Name of the user requesting the partnership. Required when `create_in_clarisa=true`
    - **external_user_comments** *(optional)*: Additional comments from the requester
    - **mis_acronym** *(optional, default "CLARISA")*: MIS system acronym for the request source
    - **request_id** *(optional)*: CLARISA partner request ID. Required when `auto_respond=true` and `create_in_clarisa=false`
    - **auth_token** *(optional)*: CLARISA Bearer token. Required when `auto_respond=true` or `create_in_clarisa=true`
    - **user_id** *(optional)*: CLARISA user ID. Required when `auto_respond=true` or `create_in_clarisa=true`
    - **auto_respond** *(optional, default false)*: If `true`, automatically submits the decision to CLARISA.
      Always `true` implicitly when `create_in_clarisa=true`

    ## Response

    ```json
    {
        "decision": "ACCEPT",
        "confidence": "high",
        "reason": "Excellent CLARISA match found (score: 0.92)",
        "match_quality": "excellent",
        "clarisa_match": { ... },
        "web_search_performed": false,
        "web_search_result": null,
        "auto_responded_to_clarisa": false,
        "clarisa_response": null
    }
    ```

    ## Response Fields

    - **decision**: `"ACCEPT"` or `"REJECT"`
    - **confidence**: `"high"`, `"medium"`, or `"low"`
    - **reason**: Human-readable explanation of the decision
    - **match_quality**: `"excellent"`, `"good"`, `"fair"`, or `"no_match"`
    - **clarisa_match**: Best CLARISA match found, or `null`
    - **web_search_performed**: Whether AI web search was triggered
    - **web_search_result**: Structured web search decision (when performed)
    - **auto_responded_to_clarisa**: Whether the decision was automatically submitted to CLARISA
    - **clarisa_response**: CLARISA API response (when `auto_respond=true`)

    ## HTTP Status Codes

    - **200**: Evaluation completed successfully (decision may be ACCEPT or REJECT)
    - **400**: Missing required fields for `auto_respond=true`
    - **500**: Internal processing error
    - **502**: Network error communicating with CLARISA (only when `auto_respond=true`)

    ## Notes

    - No caching is used in this endpoint
    - This endpoint does **not** affect the manual review frontend in any way
    - Typical response time: 2–5 s for CLARISA-only matches; 10–25 s when web search is triggered
    """
    try:
        partner_name = body.partner_name.strip()
        logger.info(f"🤖 AUTO-PARTNER-REQUEST received for: '{partner_name}'")

        raw_token = (body.auth_token or "").strip()
        if raw_token.lower().startswith("bearer "):
            raw_token = raw_token[7:].strip()
        auth_header = f"Bearer {raw_token}" if raw_token else ""

        # ------------------------------------------------------------------
        # STEP 0 — Create partner request in CLARISA (when requested)
        # ------------------------------------------------------------------
        created_request_id: Optional[int] = body.request_id

        if body.create_in_clarisa:
            missing = [
                f for f, v in [
                    ("country", body.country),
                    ("institution_type", body.institution_type),
                    ("auth_token", body.auth_token),
                    ("user_id", body.user_id),
                    ("external_user_mail", body.external_user_mail),
                    ("external_user_name", body.external_user_name),
                ]
                if not v
            ]
            if missing:
                raise HTTPException(
                    status_code=400,
                    detail=f"create_in_clarisa=true requires: {', '.join(missing)}"
                )

            logger.info(f"🔨 Creating partner request in CLARISA for: '{partner_name}'")

            # Fetch country ISO code
            country_iso = None
            try:
                countries_resp = requests.get(CLARISA_COUNTRIES_URL, timeout=30)
                countries_resp.raise_for_status()
                countries_list = countries_resp.json()
                countries_map = {c.get("name", "").strip().lower(): c.get("isoAlpha2") for c in countries_list}
                country_iso = countries_map.get(body.country.strip().lower())
                if not country_iso:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Country '{body.country}' not found in CLARISA control list."
                    )
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"Error fetching CLARISA countries: {str(e)}")

            # Fetch institution type code
            institution_type_code = None
            try:
                types_resp = requests.get(CLARISA_INSTITUTION_TYPES_URL, timeout=30)
                types_resp.raise_for_status()
                types_list = types_resp.json()
                types_map = {t.get("name", "").strip().lower(): t.get("code") for t in types_list}
                institution_type_code = types_map.get(body.institution_type.strip().lower())
                if institution_type_code is None:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Institution type '{body.institution_type}' not found in CLARISA control list."
                    )
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"Error fetching CLARISA institution types: {str(e)}")

            # Create the partner request
            create_payload = {
                "name": partner_name,
                "acronym": body.acronym or "",
                "websiteLink": body.website or "",
                "hqCountryIso": country_iso,
                "institutionTypeCode": institution_type_code,
                "externalUserMail": body.external_user_mail,
                "externalUserName": body.external_user_name,
                "externalUserComments": body.external_user_comments or "",
                "misAcronym": body.mis_acronym
            }
            try:
                create_resp = requests.post(
                    CLARISA_CREATE_URL,
                    json=create_payload,
                    headers={
                        "Authorization": auth_header,
                        "Content-Type": "application/json"
                    },
                    timeout=30
                )
                create_resp.raise_for_status()
                logger.info(f"✅ Partner request created in CLARISA for: '{partner_name}'")
            except requests.exceptions.RequestException as e:
                raise HTTPException(status_code=502, detail=f"Error creating partner request in CLARISA: {str(e)}")

            # Retrieve the newly assigned request_id
            try:
                fetch_resp = requests.get(
                    CLARISA_API_URL,
                    headers={"Authorization": auth_header},
                    timeout=30
                )
                fetch_resp.raise_for_status()
                all_requests = fetch_resp.json()
                name_lower = partner_name.lower()
                user_mail_lower = (body.external_user_mail or "").strip().lower()
                matched_request = next(
                    (
                        r for r in sorted(
                            all_requests,
                            key=lambda x: x.get("id", 0),
                            reverse=True
                        )
                        if (
                            r.get("partnerName", "").strip().lower() == name_lower
                            or name_lower in r.get("partnerName", "").strip().lower()
                            or r.get("partnerName", "").strip().lower() in name_lower
                        )
                        and r.get("externalUserMail", "").strip().lower() == user_mail_lower
                    ),
                    None
                )
                if matched_request:
                    created_request_id = matched_request.get("id")
                    logger.info(f"📋 Retrieved CLARISA request_id: {created_request_id} for '{partner_name}'")
                else:
                    logger.warning(f"⚠️  Could not retrieve request_id for '{partner_name}' — auto-respond will be skipped")
            except Exception as e:
                logger.warning(f"⚠️  Error fetching request_id after creation: {e}")

        # ------------------------------------------------------------------
        # STEP 1 — CLARISA hybrid search
        # ------------------------------------------------------------------
        try:
            search_result = search_institution_for_excel(partner_name, body.acronym)
        except Exception as e:
            logger.warning(f"⚠️  CLARISA search unavailable for '{partner_name}': {e}. Falling back to web search.")
            search_result = None

        clarisa_match_data = None
        match_quality = "no_match"
        decision = None
        confidence = "low"
        reason = ""
        web_search_performed = False
        web_search_result = None
        duplicate_check_performed = False
        duplicate_check_result = None
        fields_complete = None
        missing_fields = None
        best_match = None

        if search_result and search_result.get("best_match"):
            best_match = search_result["best_match"]
            score = best_match["final_score"]

            clarisa_match_data = {
                "clarisa_id": best_match["clarisa_id"],
                "name": best_match["name"],
                "acronym": best_match.get("acronym", ""),
                "countries": best_match.get("countries", []),
                "institution_type": best_match.get("institution_type", ""),
                "website": best_match.get("website", ""),
                "used_translation": best_match.get("used_translation", False),
                "scores": {
                    "cosine_similarity": round(best_match["cosine_similarity"], 4),
                    "fuzz_name_score": round(best_match["fuzz_name_score"], 4),
                    "fuzz_acronym_score": round(best_match["fuzz_acronym_score"], 4),
                    "final_score": round(score, 4)
                }
            }

            if score > AUTO_EXCELLENT_MIN:
                match_quality = "excellent"
            elif score >= AUTO_VERY_GOOD_MIN:
                match_quality = "very_good"
            elif score >= AUTO_GOOD_MIN:
                match_quality = "good"
            else:
                match_quality = "fair"

        # ------------------------------------------------------------------
        # STEP 2 — Decision by match-quality tier
        # ------------------------------------------------------------------
        if match_quality == "excellent":
            # Near-certain duplicate — auto-reject with no further checks.
            decision = "REJECT"
            confidence = "high"
            reason = (
                f"Institution already exists in CLARISA: '{best_match['name']}' "
                f"(score: {best_match['final_score']:.2f}). Duplicate partner requests are not accepted. "
                f"Use the existing CLARISA entry (ID: {best_match['clarisa_id']})."
            )

        elif match_quality in ("very_good", "good"):
            # High-probability match — confirm with a smaller/faster model before
            # rejecting outright. If it's NOT confirmed as the same institution,
            # fall through to STEP 3 rather than rejecting.
            duplicate_check_performed = True
            logger.info(f"   Running same-institution check: '{partner_name}' vs '{best_match['name']}'")
            dup = check_same_institution(
                requester_metadata={
                    "name": partner_name,
                    "acronym": body.acronym,
                    "website": body.website,
                    "institution_type": body.institution_type,
                    "country": body.country,
                },
                candidate_metadata=best_match
            )
            duplicate_check_result = dup

            if dup.get("success") and dup.get("same_institution"):
                decision = "REJECT"
                confidence = dup.get("confidence", "medium")
                reason = (
                    f"AI confirmed this is the same institution as the existing CLARISA entry "
                    f"'{best_match['name']}' (ID: {best_match['clarisa_id']}): {dup.get('reason', '')}"
                )
            # else: not confirmed as a duplicate — decision stays None, falls through to STEP 3

        # match_quality in ("fair", "no_match"): skip the duplicate check entirely
        # (score too low for a meaningful comparison) and fall straight through to STEP 3.

        # ------------------------------------------------------------------
        # STEP 3 — Web search + rules validation
        # Entered for: fair, no_match, and very_good/good where the duplicate
        # check did NOT confirm a match. Outcome is ACCEPT or MANUAL_REVIEW —
        # never a direct REJECT from this step (only a confirmed duplicate,
        # handled above, can produce REJECT).
        #
        # Decision is based SOLELY on the web search + rules validation outcome.
        # Field completeness is NOT a gate here — a request with every field
        # filled in still goes through this exact same review as one with
        # missing fields, and can still land in MANUAL_REVIEW if the rules
        # validation isn't confident. completeness is only tracked below as
        # informational metadata for whoever handles the manual review.
        # ------------------------------------------------------------------
        if decision is None:
            web_search_performed = True
            logger.info(f"   Triggering auto-decision web search for: '{partner_name}'")

            ws = search_institution_auto_decision(
                name=partner_name,
                country=body.country,
                website=body.website
            )

            web_search_result = {
                "approved": ws.get("approved"),
                "confidence": ws.get("confidence", "low"),
                "institution_name": ws.get("institution_name", ""),
                "institution_type": ws.get("institution_type", ""),
                "is_legal_entity": ws.get("is_legal_entity"),
                "has_research_mandate": ws.get("has_research_mandate"),
                "reason": ws.get("reason", ""),
                "summary": ws.get("summary", "")
            }

            fields_complete, missing_fields = _check_completeness(body)
            rules_passed = bool(ws.get("success") and ws.get("approved"))

            if rules_passed:
                decision = "ACCEPT"
                confidence = ws.get("confidence", "low")
                reason = ws.get("reason") or "Web search confirmed the institution meets CGIAR eligibility criteria."
            else:
                decision = "MANUAL_REVIEW"
                confidence = "low"
                reason = (
                    ws.get("reason") or ws.get("error")
                    or "AI could not confirm the institution meets CGIAR eligibility criteria."
                )

        logger.info(f"🤖 Decision: {decision} ({confidence}) — {partner_name}")

        # ------------------------------------------------------------------
        # STEP 4 — Notifications (never blocks the response on failure)
        # Only MANUAL_REVIEW notifies from here: ACCEPT/REJECT both go through
        # CLARISA's own respond endpoint below (STEP 5), which already handles
        # notifying the requester. MANUAL_REVIEW makes no CLARISA call at all,
        # so without this it would otherwise go silent.
        # ------------------------------------------------------------------
        notifications_result = None
        if decision == "MANUAL_REVIEW":
            try:
                notifications_result = notify_manual_review_pending(
                    partner_name=partner_name,
                    requester_email=body.external_user_mail,
                    requester_name=body.external_user_name,
                    request_id=created_request_id,
                    review_reason=reason
                )
            except Exception as e:
                logger.warning(f"⚠️  Notification dispatch failed (non-blocking) for '{partner_name}': {e}")

        # ------------------------------------------------------------------
        # STEP 5 — Optional: auto-respond to CLARISA (skipped for MANUAL_REVIEW —
        # the request is left "Pending" in CLARISA for a human to resolve via
        # the existing manual /api/respond-partner-request endpoint)
        # ------------------------------------------------------------------
        auto_responded = False
        clarisa_response_data = None

        if decision == "MANUAL_REVIEW":
            logger.info(f"⏸️  Decision is MANUAL_REVIEW for '{partner_name}' — leaving CLARISA request pending for human review.")
            clarisa_response_data = {
                "skipped": True,
                "reason": "Routed to manual review; awaiting human decision via the existing manual review workflow."
            }
        elif body.auto_respond or body.create_in_clarisa:
            effective_request_id = created_request_id
            if not effective_request_id or not body.auth_token or not body.user_id:
                if body.create_in_clarisa and not effective_request_id:
                    logger.warning("⚠️  Could not auto-respond: request_id was not retrieved after creation")
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="auto_respond=true requires request_id (or create_in_clarisa=true), auth_token, and user_id."
                    )
            else:
                logger.info(f"📤 Auto-responding to CLARISA request {effective_request_id}: {decision}")
                accept_flag = decision == "ACCEPT"
                reject_justification = reason if not accept_flag else None

                try:
                    fetch_response = requests.get(
                        CLARISA_API_URL,
                        headers={"Authorization": auth_header},
                        timeout=30
                    )
                    fetch_response.raise_for_status()
                    all_requests = fetch_response.json()

                    partner_request = next(
                        (pr for pr in all_requests if pr.get("id") == effective_request_id),
                        None
                    )

                    if not partner_request:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Partner request {effective_request_id} not found in CLARISA."
                        )

                    payload = {
                        "requestId": effective_request_id,
                        "userId": body.user_id,
                        "accept": accept_flag,
                        "misAcronym": partner_request.get("mis", body.mis_acronym),
                        "externalUserMail": partner_request.get("externalUserMail", body.external_user_mail or ""),
                        "externalUserName": partner_request.get("externalUserName", body.external_user_name or ""),
                        "externalUserComments": partner_request.get("externalUserComments", body.external_user_comments or "")
                    }
                    if not accept_flag:
                        payload["rejectJustification"] = reject_justification or "Rejected by automated evaluation"

                    clarisa_post = requests.post(
                        CLARISA_RESPOND_URL,
                        json=payload,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": auth_header
                        },
                        timeout=30
                    )
                    clarisa_post.raise_for_status()

                    auto_responded = True
                    clarisa_response_data = {
                        "success": True,
                        "action": "accept" if accept_flag else "reject",
                        "request_id": effective_request_id,
                        "message": f"Partner request successfully {'accepted' if accept_flag else 'rejected'}"
                    }
                    logger.info(f"✅ CLARISA auto-respond successful for request {effective_request_id}")

                except HTTPException:
                    raise
                except requests.exceptions.RequestException as e:
                    logger.error(f"❌ CLARISA auto-respond network error: {e}")
                    clarisa_response_data = {"success": False, "error": str(e)}
                    raise HTTPException(
                        status_code=502,
                        detail=f"Network error communicating with CLARISA API: {str(e)}"
                    )

        return AutoPartnerResponse(
            decision=decision,
            confidence=confidence,
            reason=reason,
            match_quality=match_quality,
            clarisa_match=clarisa_match_data,
            web_search_performed=web_search_performed,
            web_search_result=web_search_result,
            auto_responded_to_clarisa=auto_responded,
            clarisa_response=clarisa_response_data,
            duplicate_check_performed=duplicate_check_performed,
            duplicate_check_result=duplicate_check_result,
            fields_complete=fields_complete,
            missing_fields=missing_fields,
            notifications=notifications_result
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in auto-partner-request: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing automated partner request: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")