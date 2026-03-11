"""
FastAPI server for Partner Request Support
Handles Excel file upload and processing
"""
import os
import uvicorn
import tempfile
import requests
import pandas as pd
from typing import List, Dict, Optional
from logger.logger_util import get_logger
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from src.mapping_clarisa_comparison import process_partners_to_json


logger = get_logger()

# Global variables
synced_partner_requests: List[Dict] = []
CLARISA_API_URL = "https://clarisatest-back.ciat.cgiar.org/api/partner-requests"
CLARISA_RESPOND_URL = "https://clarisatest-back.ciat.cgiar.org/api/partner-requests/respond"

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
async def process_partners(file: UploadFile = File(...)):
    """
    Process an Excel file with partner requests
    
    Expected Excel format:
        - Column 0: ID (optional)
        - Column 1: partner_name (REQUIRED)
        - Column 2: acronym (optional)
        - Column 3: website (optional)
        - Column 5: country (optional)
    
    Returns:
        JSON with processed results including:
        - partners: List of partners with match info
        - stats: Processing statistics
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an Excel file (.xlsx or .xls)"
        )
    
    temp_file = None
    try:
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
        
        logger.info("🚀 Starting processing pipeline...")
        results = process_partners_to_json(df)
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
        
        # Fetch data from external API
        response = requests.get(CLARISA_API_URL, timeout=30)
        response.raise_for_status()
        
        partner_requests = response.json()
        
        # Filter only pending requests
        pending_requests = [
            pr for pr in partner_requests 
            if pr.get('requestStatus') == 'Pending'
        ]
        
        # Store in global variable
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


@app.post("/api/process-api-partners")
async def process_api_partners(partner_ids: Optional[List[int]] = Body(None)):
    """
    Process partner requests from the synced API data
    
    Args:
        partner_ids: Optional list of specific partner IDs to process.
                    If None, processes all synced partners (limited to 5 for testing)
    
    Returns:
        JSON with processed results including:
        - partners: List of partners with match info
        - stats: Processing statistics
    """
    global synced_partner_requests
    
    if not synced_partner_requests:
        raise HTTPException(
            status_code=400,
            detail="No partner requests available. Please sync first using /api/sync-partner-requests"
        )
    
    try:
        # Filter partners if specific IDs provided
        if partner_ids:
            partners_to_process = [
                pr for pr in synced_partner_requests 
                if pr.get('id') in partner_ids
            ]
        else:
            # For testing, limit to last 3 partners
            partners_to_process = synced_partner_requests[-3:]
        
        if not partners_to_process:
            raise HTTPException(
                status_code=404,
                detail="No matching partner requests found"
            )
        
        logger.info(f"🚀 Processing {len(partners_to_process)} partner requests from API")
        
        # Convert API data to DataFrame format expected by process_partners_to_json
        data_rows = []
        for pr in partners_to_process:
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
        
        # Create DataFrame
        df = pd.DataFrame(data_rows)
        
        # Reorder columns to match expected format
        # Column 0: ID, Column 1: partner_name, Column 2: acronym, Column 3: website, Column 5: country
        df_ordered = pd.DataFrame({
            'id': df['id'],
            'partner_name': df['partner_name'],
            'acronym': df['acronym'],
            'website': df['website'],
            'placeholder': '',  # Column 4 placeholder
            'country': df['country'],
        })
        
        logger.info(f"📊 Created DataFrame with {len(df_ordered)} rows")
        
        # Process using existing pipeline
        results = process_partners_to_json(df_ordered)
        
        # Add original API data to results for reference
        for i, partner_result in enumerate(results['partners']):
            if i < len(partners_to_process):
                partner_result['api_data'] = {
                    'request_id': partners_to_process[i].get('id'),
                    'request_source': partners_to_process[i].get('requestSource'),
                    'external_user': partners_to_process[i].get('externalUserName'),
                    'created_at': partners_to_process[i].get('created_at'),
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
        # Find the partner request in synced data
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
        
        # Build the payload for CLARISA API
        payload = {
            "requestId": request_id,
            "userId": user_id,
            "accept": accept,
            "misAcronym": partner_request.get('mis', 'CLARISA'),
            "externalUserMail": partner_request.get('externalUserMail', ''),
            "externalUserName": partner_request.get('externalUserName', ''),
            "externalUserComments": partner_request.get('externalUserComments', '')
        }
        
        # Add reject justification if rejecting
        if not accept:
            payload["rejectJustification"] = reject_justification or "No justification provided"
        
        # Prepare headers with authentication
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}"
        }
        
        action = "accept" if accept else "reject"
        logger.info(f"📤 Sending {action} request for partner {request_id} to CLARISA API")
        
        # Send request to CLARISA API
        response = requests.post(
            CLARISA_RESPOND_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        response.raise_for_status()
        
        logger.info(f"✅ Successfully {action}ed partner request {request_id}")
        
        # Remove from synced_partner_requests after successful response
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")