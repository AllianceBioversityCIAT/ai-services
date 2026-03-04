"""
FastAPI server for Partner Request Support
Handles Excel file upload and processing
"""
import os
import tempfile
import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from logger.logger_util import get_logger
from src.mapping_clarisa_comparison import process_partners_to_json

logger = get_logger()

app = FastAPI(
    title="Partner Request Support API",
    description="API for processing partner requests and matching with CLARISA database",
    version="1.0.0"
)

# CORS configuration - Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Next.js default ports
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
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an Excel file (.xlsx or .xls)"
        )
    
    # Create temporary file to save upload
    temp_file = None
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            contents = await file.read()
            temp_file.write(contents)
            temp_path = temp_file.name
        
        logger.info(f"📁 Processing file: {file.filename}")
        
        # Read Excel file
        try:
            df = pd.read_excel(temp_path, engine='openpyxl')
            logger.info(f"✅ {len(df)} rows loaded from Excel")
        except Exception as e:
            logger.error(f"❌ Error reading Excel: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Error reading Excel file: {str(e)}"
            )
        
        # Validate minimum columns
        if len(df.columns) < 2:
            raise HTTPException(
                status_code=400,
                detail="Excel file must have at least 2 columns (ID and partner_name)"
            )
        
        # Validate that column 1 (partner_name) has data
        if df.iloc[:, 1].isna().all():
            raise HTTPException(
                status_code=400,
                detail="Partner name column (column 1) is empty"
            )
        
        # Process the data
        logger.info("🚀 Starting processing pipeline...")
        results = process_partners_to_json(df)
        logger.info("✅ Processing completed successfully")
        
        return JSONResponse(content=results)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"❌ Error processing file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )
    finally:
        # Clean up temporary file
        if temp_file and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
                logger.info("🗑️  Temporary file cleaned up")
            except Exception as e:
                logger.warning(f"⚠️  Could not delete temporary file: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
