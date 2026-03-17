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
from dotenv import load_dotenv
from config.config_util import BR
from typing import List, Dict, Optional
from logger.logger_util import get_logger
from botocore.exceptions import ClientError
from fastapi.middleware.cors import CORSMiddleware
from src.web_search import search_institution_online
from src.populate_clarisa_db import sync_clarisa_institutions
from fastapi.responses import JSONResponse, StreamingResponse
from src.mapping_clarisa_comparison import process_partners_to_json
from fastapi import FastAPI, File, UploadFile, HTTPException, Body, Form
from src.supabase_client import get_cached_results_by_name, cache_results_batch, count_institutions


logger = get_logger()
load_dotenv()

synced_partner_requests: List[Dict] = []
CLARISA_API_URL = os.getenv("CLARISA_PARTNER_REQUESTS_URL")
CLARISA_CREATE_URL = os.getenv("CLARISA_CREATE_URL")
CLARISA_RESPOND_URL = os.getenv("CLARISA_RESPOND_URL")
CLARISA_COUNTRIES_URL = os.getenv("CLARISA_COUNTRIES_URL")
CLARISA_INSTITUTION_TYPES_URL = os.getenv("CLARISA_INSTITUTION_TYPES_URL")


app = FastAPI(
    title="Partner Request Support API",
    description="API for processing partner requests and matching with CLARISA database",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint - API info"""
    return {
        "name": "Partner Request Support API",
        "version": "1.0.0",
        "status": "online"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/api/process-partners")
async def process_partners(
    file: UploadFile = File(...),
    user_email: str = Form(...),
    user_name: str = Form(...),
    auth_token: str = Form(...),
    create_requests: bool = Form(default=True)
):
    """
    Process an Excel file with partner requests.
    First creates the partner requests in CLARISA, then processes them.
    
    Expected Excel format:
        - Column 0: ID (optional)
        - Column 1: partner_name (REQUIRED)
        - Column 2: acronym (optional)
        - Column 3: website (optional)
        - Column 4: institution_type (REQUIRED - must match CLARISA control list)
        - Column 5: country (REQUIRED - must match CLARISA control list)
        - Column 6: category_1 (optional)
        - Column 7: category_2 (optional)
    
    Note: Country and Institution Type are validated against CLARISA control lists.
          If a value is not found in the control list or is missing, the partner request
          will NOT be created and will be marked as failed.
    
    Args:
        file: Excel file to process
        user_email: Email of the user creating the requests
        user_name: Name of the user creating the requests
        auth_token: Authentication token for CLARISA API
        create_requests: Whether to create partner requests in CLARISA first
    
    Returns:
        JSON with processed results including:
        - partners: List of partners with match info
        - stats: Processing statistics
        - creation_info: Info about request creation (if create_requests=True)
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an Excel file (.xlsx or .xls)"
        )
    
    temp_file = None
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
            countries_list = []
            countries_map = {}
            try:
                countries_response = requests.get(CLARISA_COUNTRIES_URL, timeout=30)
                
                if countries_response.status_code == 200:
                    countries_list = countries_response.json()
                    for country in countries_list:
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
            institution_types_list = []
            institution_types_map = {} 
            try:
                institution_types_response = requests.get(CLARISA_INSTITUTION_TYPES_URL, timeout=30)
                
                if institution_types_response.status_code == 200:
                    institution_types_list = institution_types_response.json()
                    for inst_type in institution_types_list:
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


@app.get("/api/sync-partner-requests")
async def sync_partner_requests():
    """
    Synchronize partner requests from external CLARISA API
    
    Returns:
        JSON with:
        - count: Number of partner requests found
        - pending_requests: List of pending partner requests
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


@app.post("/api/sync-clarisa-institutions")
async def sync_clarisa_institutions_endpoint(delete_obsolete: bool = Body(True)):
    """
    Manually trigger synchronization of CLARISA institutions database
    
    This endpoint allows forcing a sync of the institutions database with CLARISA API.
    It compares the current database with CLARISA and only processes new or modified institutions.
    
    Args:
        delete_obsolete: Whether to delete institutions that no longer exist in CLARISA (default: True)
    
    Returns:
        JSON with sync statistics including:
        - institutions_before: Count before sync
        - institutions_after: Count after sync
        - new_institutions: Number of new institutions added
        - modified_institutions: Number of institutions updated
        - unchanged_institutions: Number of institutions that didn't change
        - obsolete_institutions: Number of obsolete institutions found
        - total_processed: Total institutions that required embedding generation
        - message: User-friendly message about the sync result
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


@app.post("/api/process-api-partners")
async def process_api_partners(partner_ids: Optional[List[int]] = Body(None)):
    """
    Process partner requests from the synced API data.
    Uses cache to avoid re-processing already processed requests.
    
    Args:
        partner_ids: Optional list of specific partner IDs to process.
                    If None, processes all synced partners
    
    Returns:
        JSON with processed results including:
        - partners: List of partners with match info
        - stats: Processing statistics
        - cache_info: Cache hit/miss statistics
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


@app.post("/api/respond-partner-request")
async def respond_partner_request(
    request_id: int = Body(...),
    user_id: int = Body(...),
    accept: bool = Body(...),
    auth_token: str = Body(...),
    reject_justification: Optional[str] = Body(None)
):
    """
    Accept or reject a partner request
    
    Args:
        request_id: ID of the partner request to respond to
        user_id: ID of the authenticated user
        accept: True to accept, False to reject
        auth_token: Bearer token for authentication
        reject_justification: Optional text when rejecting
    
    Returns:
        JSON with success status and message
    """
    global synced_partner_requests
    
    try:
        partner_request = None
        for pr in synced_partner_requests:
            if pr.get('id') == request_id:
                partner_request = pr
                break
        
        if not partner_request:
            raise HTTPException(
                status_code=404,
                detail=f"Partner request {request_id} not found. Please sync first."
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
        
        synced_partner_requests = [
            pr for pr in synced_partner_requests 
            if pr.get('id') != request_id
        ]
        
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


@app.post("/api/manual-web-search")
async def manual_web_search(
    partner_name: str = Body(...),
    country: Optional[str] = Body(None),
    website: Optional[str] = Body(None)
):
    """
    Manually trigger a web search for a partner institution.
    Used when match_quality is 'fair' or 'good' and user wants additional information.
    
    Args:
        partner_name: Name of the partner institution
        country: Country of the institution (optional)
        website: Website of the institution (optional)
        
    Returns:
        JSON with web search results
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


@app.get("/api/download-template")
async def download_template():
    """
    Download the Excel template from S3.
    Uses the same AWS credentials as Bedrock.
    
    Returns:
        StreamingResponse with the Excel file
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")