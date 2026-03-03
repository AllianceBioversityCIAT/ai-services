import os
from logger.logger_util import get_logger
from src.mapping_clarisa_comparison import run_pipeline

logger = get_logger()


if __name__ == "__main__":
    """
    Executes the mapping pipeline CGSpace → CLARISA
    
    Excel format:
        - Column 0: ID (optional)
        - Column 1: partner_name (REQUIRED)
        - Column 2: acronym (optional)
        - Other columns are preserved in the result
    
    Configuration:
        Adjust constants at the beginning of the file:
        - THRESHOLD_EMBEDDINGS: Threshold for vector search (default: 0.3)
        - THRESHOLD_FINAL: Threshold for valid match (default: 0.6)
        - NAME_WEIGHT / ACRONYM_WEIGHT: Weights in combined search
        - COSINE_WEIGHT / FUZZ_NAME_WEIGHT / FUZZ_ACRONYM_WEIGHT: Weights in final score
    """
    # Excel file to process
    excel_file = "File_test_pr.xlsx"
    
    if not os.path.exists(excel_file):
        logger.error(f"❌ Error: File '{excel_file}' not found")
        logger.info("📝 Expected Excel format:")
        logger.info("   Column 0: ID (optional)")
        logger.info("   Column 1: partner_name (institution name)")
        logger.info("   Column 2: acronym (acronym, optional)")
    else:
        run_pipeline(excel_file)