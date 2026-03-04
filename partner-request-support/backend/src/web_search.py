"""
Web search module for institutions using TWO-PHASE approach:
- Phase 1: Exploratory search with OpenAI gpt-5-mini (low cost, gather all info)
- Phase 2: Analysis & structuring with AWS Bedrock Claude Sonnet 4.6 (reasoning, formatting)

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
import json
import boto3
from openai import OpenAI
from dotenv import load_dotenv
from typing import Optional, Dict, Any
from logger.logger_util import get_logger

load_dotenv()
logger = get_logger()


# OpenAI client (for Phase 1: search)
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# AWS Bedrock client (for Phase 2: analysis)
bedrock_client = boto3.client(
    service_name='bedrock-runtime',
    region_name=os.getenv("AWS_REGION", "us-east-1"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID_BR"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY_BR")
)


# ============================================================================
# PHASE 1: EXPLORATORY SEARCH (OpenAI gpt-5-mini)
# ============================================================================

def _phase1_exploratory_search(
    name: str,
    country: Optional[str] = None,
    website: Optional[str] = None
) -> Dict[str, Any]:
    """
    Phase 1: Exploratory web search to gather ALL available information
    Uses OpenAI gpt-5-mini with web search - low cost, high information gathering
    
    Args:
        name: Institution name
        country: Country (optional)
        website: Official website (optional)
        
    Returns:
        dict: {
            "success": bool,
            "raw_content": str (all information found),
            "sources": list of URLs,
            "search_type": "focused" | "open",
            "error": str (if failure)
        }
    """
    try:
        # Build search query - NO FORMAT RESTRICTIONS, just gather info
        query = f"""
Find ALL available information about this institution: "{name}"
"""
        if country:
            query += f"\nCountry: {country}"
        if website:
            query += f"\nOfficial website: {website}"
        
        query += """

Please gather and report ALL information you can find about:
- Official full name and any acronyms
- Type of institution (university, research center, government agency, NGO, etc.)
- Legal status (is it an independent legal entity or part of another organization?)
- Parent organization (if it's not independent)
- Location (country, city)
- Official website
- Research activities and mandate (if any)
- Main focus areas and activities
- Any other relevant institutional information

DO NOT format as JSON. Just provide a comprehensive narrative with all the information you find.
Be thorough - include everything that might be relevant.
"""
        
        # Setup tools for search
        tools = [{"type": "web_search"}]
        
        # If website provided, add focused search on that domain
        if website and str(website).strip():
            domain = _extract_domain(str(website).strip())
            if domain:
                tools = [{
                    "type": "web_search",
                    "filters": {
                        "allowed_domains": [domain]
                    }
                }]
                search_type = "focused"
            else:
                search_type = "open"
        else:
            search_type = "open"
        
        # Execute search with OpenAI
        response = openai_client.responses.create(
            model="gpt-5-mini",
            reasoning={"effort": "low"},  # Low effort = faster, cheaper
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
            "raw_content": response.output_text,
            "sources": sources,
            "search_type": search_type,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"⚠️  Phase 1 search error for '{name}': {str(e)}")
        return {
            "success": False,
            "raw_content": None,
            "sources": [],
            "search_type": None,
            "error": str(e)
        }


# ============================================================================
# PHASE 2: ANALYSIS & FORMATTING (AWS Bedrock Claude Sonnet 4.6)
# ============================================================================

def _phase2_analyze_and_format(
    institution_name: str,
    raw_content: str,
    sources: list,
    search_type: str
) -> str:
    """
    Phase 2: Analyze all gathered information and format it beautifully
    Uses AWS Bedrock Claude Sonnet 4.6 - powerful reasoning and formatting
    
    Args:
        institution_name: Original institution name searched
        raw_content: All information gathered in Phase 1
        sources: List of source URLs
        search_type: "focused" or "open"
        
    Returns:
        str: Beautifully formatted report ready for Excel cell
    """
    try:
        # Build analysis prompt for Claude
        prompt = f"""You are analyzing information about an institution for the CGIAR partnership database.

INSTITUTION SEARCHED: {institution_name}

INFORMATION GATHERED FROM WEB SEARCH:
{raw_content}

SOURCES CONSULTED:
{chr(10).join([f"• {url}" for url in sources[:10]])}

Your task is to analyze ALL this information and create a well-structured report following this EXACT format:

----------------------------------------------------------------------------------

📋 OFFICIAL NAME
   [Full official name - be specific]

🏢 LEGAL STATUS
   Is Legal Entity: [YES / NO / UNCLEAR - based on evidence]
   Parent Organization: [Name if part of larger org, or "N/A" if independent]

🏛️ INSTITUTION TYPE (CGIAR Classification)
   [Choose the most specific category from:
   - University or academic institution
   - National/local research institution
   - International/regional research institution
   - Government entity (ministry/department/agency)
   - Bilateral development agency (e.g., USAID, DFID)
   - International/regional financial institution
   - UN entity or international organization
   - NGO
   - Private company]

🔬 RESEARCH MANDATE
   Has Research Mandate: [YES / NO / UNCLEAR - based on evidence]
   Brief Description: [If YES: 1-2 sentences about research focus and activities]

🌐 WEBSITE
   [Official website URL]

📍 LOCATION
   [Country, City]

📚 SOURCES CONSULTED (top 3-5)
   • [domain1] - [What you found here]
   • [domain2] - [What you found here]
   • [domain3] - [What you found here]

----------------------------------------------------------------------------------
   
IMPORTANT GUIDELINES:
1. Be DECISIVE but HONEST:
   - If evidence clearly shows something, state it as YES or NO
   - Only use UNCLEAR when evidence is genuinely ambiguous or conflicting
   - Use ALL the information provided to make informed decisions

2. For Legal Entity status:
   - YES if it's an independent organization with legal personality
   - NO if it's a department/unit within a larger organization
   - Consider: Does it have its own legal registration? Can it sign contracts independently?

3. For Research Mandate:
   - YES if research is a core mission/activity
   - NO if it's purely operational/administrative
   - Look for evidence in mission statements, activities, publications

4. Institution Type: Be specific and choose the BEST fit from CGIAR categories

5. Format sources with brief context about what information came from each

OUTPUT ONLY THE FORMATTED REPORT. No additional commentary."""

        # Call AWS Bedrock Claude Sonnet 4.6
        response = bedrock_client.invoke_model(
            modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        formatted_result = response_body['content'][0]['text']
        logger.info("Result from Phase 2 analysis:\n" + formatted_result)
        
        return formatted_result
        
    except Exception as e:
        logger.error(f"⚠️  Phase 2 analysis error: {str(e)}")
        # Return error message in same format
        return f"""================================================================================

❌ ERROR IN ANALYSIS

Unable to analyze information for: {institution_name}
Error: {str(e)}

RAW SEARCH RESULTS (Phase 1):
{raw_content[:500]}...

================================================================================"""


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def _extract_domain(website: str) -> str:
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


# ============================================================================
# MAIN SEARCH FUNCTION (Coordinates both phases)
# ============================================================================

def search_institution_online(
    name: str,
    country: Optional[str] = None,
    website: Optional[str] = None
) -> Dict[str, Any]:
    """
    TWO-PHASE search for institution information:
    Phase 1: Exploratory search (OpenAI gpt-5-mini) - gather all info
    Phase 2: Analysis & formatting (AWS Bedrock Claude Sonnet 4.6) - structure and format
    
    Args:
        name: Institution name
        country: Country (optional, improves search)
        website: Official website (optional, enables focused search)
        
    Returns:
        dict: {
            "success": bool,
            "formatted_result": str (beautifully formatted report for Excel),
            "error": str (if error occurs)
        }
    """
    try:
        # Validate input
        if not name or str(name).strip() == "":
            return {
                "success": False,
                "formatted_result": "❌ ERROR: Institution name is required",
                "error": "Institution name is required"
            }
        
        name = str(name).strip()
        
        logger.info(f"🔍 Starting TWO-PHASE search for: {name}")
        
        # ===== PHASE 1: EXPLORATORY SEARCH =====
        logger.info("   Phase 1/2: Gathering information (OpenAI)...")
        phase1_result = _phase1_exploratory_search(name, country, website)
        
        if not phase1_result["success"]:
            return {
                "success": False,
                "formatted_result": f"❌ ERROR in Phase 1: {phase1_result['error']}",
                "error": phase1_result["error"]
            }
        
        # ===== PHASE 2: ANALYSIS & FORMATTING =====
        logger.info("   Phase 2/2: Analyzing and formatting (Claude Sonnet 4.6)...")
        formatted_result = _phase2_analyze_and_format(
            institution_name=name,
            raw_content=phase1_result["raw_content"],
            sources=phase1_result["sources"],
            search_type=phase1_result["search_type"]
        )
        
        logger.info(f"✅ Search completed for: {name}")
        
        return {
            "success": True,
            "formatted_result": formatted_result,
            "error": None
        }
    
    except Exception as e:
        logger.error(f"\n⚠️  Web search error for '{name}': {str(e)}")
        return {
            "success": False,
            "formatted_result": f"❌ ERROR: {str(e)}",
            "error": str(e)
        }


# ============================================================================
# TEST FUNCTION
# ============================================================================

def test_search(name: str, country: str = None, website: str = None):
    """
    Test function to verify TWO-PHASE web search functionality
    
    Usage:
        from src.web_search import test_search
        test_search("Stanford University", "United States", "https://www.stanford.edu")
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"🔍 TESTING TWO-PHASE SEARCH")
    logger.info(f"{'='*80}")
    logger.info(f"Institution: {name}")
    if country:
        logger.info(f"Country: {country}")
    if website:
        logger.info(f"Website: {website}")
    logger.info(f"{'='*80}\n")
    
    result = search_institution_online(name, country, website)
    
    # Display result
    if result["success"]:
        logger.info("\n" + result["formatted_result"])
    else:
        logger.error(f"\n❌ Search failed: {result['error']}")
    
    return result
