"""
Module to load institution data from the CLARISA API
"""
import os
import requests
from dotenv import load_dotenv
from typing import List, Dict, Optional
from logger.logger_util import get_logger
from src.utils import format_countries, extract_institution_type, safe_str

load_dotenv()
logger = get_logger()

CLARISA_API_URL = os.getenv('CLARISA_API_URL')


def fetch_clarisa_institutions() -> Optional[List[Dict]]:
    """
    Fetches all institutions from the CLARISA API
    
    Returns:
        List[Dict]: List of institutions in CLARISA JSON format
        None: If there is an error in the request
    """
    try:
        logger.info("📡 Connecting to the CLARISA API...")
        response = requests.get(CLARISA_API_URL, timeout=30)
        response.raise_for_status()
        
        institutions = response.json()
        logger.info(f"✅ Retrieved {len(institutions)} institutions from CLARISA")
        
        return institutions
    
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error fetching data from CLARISA: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return None


def parse_clarisa_institution(raw_institution: Dict) -> Dict:
    """
    Parses an institution from CLARISA format to our DB format
    
    Args:
        raw_institution: Dictionary with CLARISA data
        
    Returns:
        Dict: Dictionary with parsed data for the DB
    """
    clarisa_id = raw_institution.get('code')
    name = safe_str(raw_institution.get('name') or '')
    acronym = safe_str(raw_institution.get('acronym') or '')
    website = safe_str(raw_institution.get('websiteLink') or '')
    
    country_offices = raw_institution.get('countryOfficeDTO', [])
    countries = format_countries(country_offices)
    
    institution_type_dict = raw_institution.get('institutionType', {})
    institution_type = extract_institution_type(institution_type_dict)
    
    return {
        'clarisa_id': clarisa_id,
        'name': name,
        'acronym': acronym,
        'website': website,
        'countries': countries,
        'institution_type': institution_type
    }


def get_all_parsed_institutions() -> List[Dict]:
    """
    Fetches and parses all institutions from CLARISA
    
    Returns:
        List[Dict]: List of parsed institutions
    """
    raw_institutions = fetch_clarisa_institutions()
    
    if not raw_institutions:
        return []
    
    parsed_institutions = []
    
    logger.info("🔄 Parsing institutions...")
    for raw_inst in raw_institutions:
        try:
            parsed_inst = parse_clarisa_institution(raw_inst)
            
            if parsed_inst['name']:
                parsed_institutions.append(parsed_inst)
            else:
                logger.warning(f"⚠️  Institution without name (ID: {parsed_inst.get('clarisa_id')})")
        
        except Exception as e:
            logger.warning(f"⚠️  Error parsing institution: {e}")
            continue
    
    logger.info(f"✅ {len(parsed_institutions)} institutions parsed successfully")
    
    return parsed_institutions
