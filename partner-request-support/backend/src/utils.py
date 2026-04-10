"""
Common utilities for the CLARISA institution mapping project
"""
import re
import unicodedata


def clean_text_for_matching(text):
    """
    Full normalization for string matching (RapidFuzz)
    Removes accents, converts to lowercase, removes special characters
    
    Args:
        text: Text to normalize
        
    Returns:
        str: Normalized text for comparison
    """
    if not isinstance(text, str):
        return ""

    text = text.lower()

    text = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )

    text = re.sub(r"[^\w\s()]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def safe_str(value):
    """
    Safely converts a value to a string, handling None and NaN
    
    Args:
        value: Value to convert
        
    Returns:
        str: String representation of the value or "" if None/NaN
    """
    if value is None:
        return ""
    
    str_val = str(value)
    
    if str_val.lower() in ['nan', 'none', 'null']:
        return ""
    
    return str_val.strip()


def format_countries(country_offices):
    """
    Extracts country names from the CLARISA countryOfficeDTO structure
    
    Args:
        country_offices: List of dictionaries with office information
        
    Returns:
        list: List of country names (strings)
    """
    if not country_offices or not isinstance(country_offices, list):
        return []
    
    countries = []
    for office in country_offices:
        if isinstance(office, dict) and 'name' in office:
            country_name = office.get('name')
            if country_name and isinstance(country_name, str):
                country_name = country_name.strip()
                if country_name and country_name not in countries:
                    countries.append(country_name)
    
    return countries


def extract_institution_type(institution_type_dict):
    """
    Extracts only the name of the institution type
    
    Args:
        institution_type_dict: Dictionary with 'code' and 'name'
        
    Returns:
        str: Name of the institution type or "" if not available
    """
    if not institution_type_dict or not isinstance(institution_type_dict, dict):
        return ""
    
    return safe_str(institution_type_dict.get('name') or '')
