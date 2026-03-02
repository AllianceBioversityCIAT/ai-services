"""
Web search module for institutions using OpenAI Web Search
Used as fallback when no match is found in CLARISA

CGIAR Institution Validation Rules (applied in queries):
- Institutions should be legal entities (or affiliated with one)
- Specific classification types:
  * Universities/Academic institutions
  * National/local research institutions
  * International/regional research institutions
  * Government entities (ministries/departments/agencies)
  * Bilateral development agencies (USAID, DFID, etc.)
  * International/regional financial institutions (World Bank, etc.)
  * International organizations (UN entities)
  * NGOs and private entities
- Research mandate is important for eligibility
"""
import os
import re
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_domain(website: str) -> str:
    """
    Extracts the main domain from a URL
    
    Args:
        website: Complete URL (e.g., "https://www.example.edu/page")
        
    Returns:
        str: Clean domain (e.g., "example.edu")
    """
    if not website:
        return ""
    
    # Remove protocol
    domain = re.sub(r'^https?://', '', website)
    # Remove www.
    domain = re.sub(r'^www\.', '', domain)
    # Remove path
    domain = domain.split('/')[0]
    # Remove port if exists
    domain = domain.split(':')[0]
    
    return domain


def search_institution_online(
    name: str,
    country: Optional[str] = None,
    website: Optional[str] = None
) -> Dict[str, Any]:
    """
    Searches for institution information on the internet using OpenAI Web Search
    
    Dual strategy:
    1. If website provided: focused search on that domain
    2. Without website: open search with improved query
    
    Args:
        name: Institution name
        country: Country (optional, improves search)
        website: Official website (optional, enables focused search)
        
    Returns:
        dict: {
            "success": bool,
            "data": dict with extracted information,
            "sources": list of URLs used,
            "search_type": "focused" | "open",
            "error": str (if error occurs)
        }
    """
    try:
        # Validate input
        if not name or str(name).strip() == "":
            return {
                "success": False,
                "error": "Institution name is required",
                "data": None,
                "sources": []
            }
        
        name = str(name).strip()
        
        # STRATEGY 1: Focused search if website is provided
        if website and str(website).strip():
            domain = extract_domain(str(website).strip())
            
            if domain:
                tools = [{
                    "type": "web_search",
                    "filters": {
                        "allowed_domains": [domain]
                    }
                }]
                
                query = f"""
Search in {domain} for official information about: {name}

Extract the following information in a clear, structured format:

1. BASIC INFORMATION:
   - Official full name
   - Acronym (if any)
   - Country/location
   - Official website

2. LEGAL STATUS:
   - Is it a legal entity? (Yes/No/Unknown)
   - If not a legal entity, what is the parent/affiliated organization that is a legal entity?

3. INSTITUTION TYPE (be specific):
   - University or academic institution
   - National/local research institution
   - International/regional research institution
   - Government entity (ministry/department/agency at any level)
   - Bilateral development agency (e.g., USAID, DFID)
   - International/regional financial institution (e.g., development banks)
   - International organization (e.g., UN entities)
   - NGO
   - Private company or commercial entity
   - Other (specify)

4. RESEARCH MANDATE:
   - Does it have a significant research mandate? (Yes/No/Unknown)
   - Brief description of its main activities and focus areas (1-2 sentences)

If any information is not available, indicate "Not found".
"""
                
                search_type = "focused"
            else:
                # If domain is invalid, do open search
                tools = [{"type": "web_search"}]
                query = _build_open_query(name, country)
                search_type = "open"
        
        # STRATEGY 2: Open search
        else:
            tools = [{"type": "web_search"}]
            query = _build_open_query(name, country)
            search_type = "open"
        
        # Execute search with OpenAI
        response = client.responses.create(
            model="gpt-5-mini",
            reasoning={"effort": "medium"},
            tools=tools,
            tool_choice="required",
            include=["web_search_call.action.sources"],
            input=query
        )
        
        # Extract sources (URLs)
        sources = []
        if hasattr(response, 'web_search_call') and hasattr(response.web_search_call, 'action'):
            sources = getattr(response.web_search_call.action, 'sources', [])
        
        return {
            "success": True,
            "data": {
                "raw_response": response.output_text,
                "name": name,
                "country": country,
                "website": website
            },
            "sources": sources,
            "search_type": search_type,
            "error": None
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": None,
            "sources": [],
            "search_type": None
        }


def _build_open_query(name: str, country: Optional[str] = None) -> str:
    """
    Builds query for open search (without website)
    
    Args:
        name: Institution name
        country: Country (optional)
        
    Returns:
        str: Optimized query for OpenAI
    """
    query = f'Find official information about the institution: "{name}"'
    
    if country:
        query += f' located in {country}'
    
    query += """

Extract the following information in a clear, structured format:

1. BASIC INFORMATION:
   - Official full name
   - Acronym (if any)
   - Country/location
   - Official website

2. LEGAL STATUS:
   - Is it a legal entity? (Yes/No/Unknown)
   - If not a legal entity, what is the parent/affiliated organization that is a legal entity?

3. INSTITUTION TYPE (be specific):
   - University or academic institution
   - National/local research institution
   - International/regional research institution
   - Government entity (ministry/department/agency at any level)
   - Bilateral development agency (e.g., USAID, DFID)
   - International/regional financial institution (e.g., development banks)
   - International organization (e.g., UN entities)
   - NGO
   - Private company or commercial entity
   - Other (specify)

4. RESEARCH MANDATE:
   - Does it have a significant research mandate? (Yes/No/Unknown)
   - Brief description of its main activities and focus areas (1-2 sentences)

Prioritize official sources (.edu, .org, .gov, official institutional websites).
If any information is not available, indicate "Not found".
"""
    
    return query


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def test_search(name: str, country: str = None, website: str = None):
    """
    Test function to verify web search functionality
    
    Usage:
        from src.web_search import test_search
        test_search("Stanford University", "United States", "https://www.stanford.edu")
    """
    print(f"\n{'='*70}")
    print(f"Searching: {name}")
    if country:
        print(f"Country: {country}")
    if website:
        print(f"Website: {website}")
    print(f"{'='*70}\n")
    
    result = search_institution_online(name, country, website)
    
    if result["success"]:
        print(f"✅ Search successful ({result['search_type']})")
        print(f"\n{result['data']['raw_response']}")
        
        if result["sources"]:
            print(f"\n📚 Sources used:")
            for i, source in enumerate(result["sources"], 1):
                print(f"  {i}. {source}")
    else:
        print(f"❌ Error: {result['error']}")
    
    print(f"\n{'='*70}\n")
    return result
