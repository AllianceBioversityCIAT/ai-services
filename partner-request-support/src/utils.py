"""
Utilidades comunes para el proyecto de mapeo de instituciones CLARISA
"""
import re
import unicodedata


def clean_text_basic(text):
    """
    Limpieza BÁSICA para embeddings (mantiene acentos, mayúsculas)
    Solo normaliza espacios y trim
    
    Args:
        text: Texto a limpiar
        
    Returns:
        str: Texto con limpieza básica
    """
    if not isinstance(text, str):
        return ""
    
    # Solo normalizar espacios múltiples y trim
    text = re.sub(r"\s+", " ", text).strip()
    
    return text


def clean_text_for_matching(text):
    """
    Normalización COMPLETA para string matching (RapidFuzz)
    Remueve acentos, lowercase, sin caracteres especiales
    
    Args:
        text: Texto a normalizar
        
    Returns:
        str: Texto normalizado para comparación
    """
    if not isinstance(text, str):
        return ""

    text = text.lower()

    # Remover acentos
    text = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )

    # Remover caracteres especiales (mantener paréntesis para siglas)
    text = re.sub(r"[^\w\s()]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


# Alias para compatibilidad con código legacy
def clean_text(text):
    """
    Alias para clean_text_for_matching (compatibilidad)
    """
    return clean_text_for_matching(text)


def safe_str(value):
    """
    Convierte un valor a string de forma segura, manejando None y NaN
    
    Args:
        value: Valor a convertir
        
    Returns:
        str: String del valor o "" si es None/NaN
    """
    if value is None:
        return ""
    
    str_val = str(value)
    
    # Manejar valores NaN de pandas
    if str_val.lower() in ['nan', 'none', 'null']:
        return ""
    
    return str_val.strip()


def format_countries(country_offices):
    """
    Extrae los nombres de países de la estructura countryOfficeDTO de CLARISA
    
    Args:
        country_offices: Lista de diccionarios con información de oficinas
        
    Returns:
        list: Lista de nombres de países (strings)
    """
    if not country_offices or not isinstance(country_offices, list):
        return []
    
    countries = []
    for office in country_offices:
        if isinstance(office, dict) and 'name' in office:
            country_name = office.get('name')
            # Validar que no sea None antes de hacer strip()
            if country_name and isinstance(country_name, str):
                country_name = country_name.strip()
                if country_name and country_name not in countries:
                    countries.append(country_name)
    
    return countries


def extract_institution_type(institution_type_dict):
    """
    Extrae solo el nombre del tipo de institución
    
    Args:
        institution_type_dict: Diccionario con 'code' y 'name'
        
    Returns:
        str: Nombre del tipo de institución o ""
    """
    if not institution_type_dict or not isinstance(institution_type_dict, dict):
        return ""
    
    # Usar 'or' para manejar None correctamente
    return safe_str(institution_type_dict.get('name') or '')
