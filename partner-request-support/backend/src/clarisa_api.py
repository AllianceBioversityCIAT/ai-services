"""
Módulo para cargar datos de instituciones desde la API de CLARISA
"""
import os
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

CLARISA_API_URL = os.getenv('CLARISA_API_URL')


def fetch_clarisa_institutions() -> Optional[List[Dict]]:
    """
    Obtiene todas las instituciones desde la API de CLARISA
    
    Returns:
        List[Dict]: Lista de instituciones en formato JSON de CLARISA
        None: Si hay error en la petición
    """
    try:
        print("📡 Conectando a la API de CLARISA...")
        response = requests.get(CLARISA_API_URL, timeout=30)
        response.raise_for_status()
        
        institutions = response.json()
        print(f"✅ Se obtuvieron {len(institutions)} instituciones de CLARISA")
        
        return institutions
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al obtener datos de CLARISA: {e}")
        return None
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return None


def parse_clarisa_institution(raw_institution: Dict) -> Dict:
    """
    Parsea una institución del formato de CLARISA al formato de nuestra DB
    
    Args:
        raw_institution: Diccionario con datos de CLARISA
        
    Returns:
        Dict: Diccionario con datos parseados para la DB
    """
    from src.utils import format_countries, extract_institution_type, safe_str
    
    # Extraer información básica
    clarisa_id = raw_institution.get('code')
    # Usar 'or' para manejar None: si get() retorna None, usar ''
    name = safe_str(raw_institution.get('name') or '')
    acronym = safe_str(raw_institution.get('acronym') or '')
    website = safe_str(raw_institution.get('websiteLink') or '')
    
    # Extraer países
    country_offices = raw_institution.get('countryOfficeDTO', [])
    countries = format_countries(country_offices)
    
    # Extraer tipo de institución
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
    Obtiene y parsea todas las instituciones de CLARISA
    
    Returns:
        List[Dict]: Lista de instituciones parseadas
    """
    raw_institutions = fetch_clarisa_institutions()
    
    if not raw_institutions:
        return []
    
    parsed_institutions = []
    
    print("🔄 Parseando instituciones...")
    for raw_inst in raw_institutions:
        try:
            parsed_inst = parse_clarisa_institution(raw_inst)
            
            # Validar que tenga al menos un nombre
            if parsed_inst['name']:
                parsed_institutions.append(parsed_inst)
            else:
                print(f"⚠️  Institución sin nombre (ID: {parsed_inst.get('clarisa_id')})")
        
        except Exception as e:
            print(f"⚠️  Error parseando institución: {e}")
            continue
    
    print(f"✅ {len(parsed_institutions)} instituciones parseadas exitosamente")
    
    return parsed_institutions
