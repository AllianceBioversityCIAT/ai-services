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


openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

        tools = [{"type": "web_search"}]
        
        search_type = "open"
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
                logger.info(f"   Using focused search on domain: {domain}")
            else:
                logger.info(f"   Invalid website domain '{website}' - using open search")
                search_type = "open"
        
        response = openai_client.responses.create(
            model="gpt-5-mini",
            reasoning={"effort": "low"},
            tools=tools,
            tool_choice="required",
            include=["web_search_call.action.sources"],
            input=query
        )
        
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
        error_message = str(e)
        
        if "Invalid domain" in error_message or "invalid_request_error" in error_message:
            user_message = f"Could not perform web search: The website URL provided appears to be invalid. Performing general web search instead."
            logger.warning(f"⚠️  Invalid domain for '{name}': {website}")
        elif "API key" in error_message.lower():
            user_message = "Web search temporarily unavailable (API configuration issue)"
            logger.error(f"⚠️  API key issue for '{name}': {error_message}")
        elif "rate limit" in error_message.lower():
            user_message = "Web search temporarily unavailable (rate limit reached)"
            logger.error(f"⚠️  Rate limit for '{name}': {error_message}")
        else:
            user_message = f"Web search could not be completed. Please try again later."
            logger.error(f"⚠️  Phase 1 search error for '{name}': {error_message}")
        
        return {
            "success": False,
            "raw_content": None,
            "sources": [],
            "search_type": None,
            "error": user_message
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
        
        response_body = json.loads(response['body'].read())
        formatted_result = response_body['content'][0]['text']
        logger.info("Result from Phase 2 analysis:\n" + formatted_result)
        
        return formatted_result
        
    except Exception as e:
        logger.error(f"⚠️  Phase 2 analysis error: {str(e)}")
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
    Extracts and validates the main domain from a URL
    
    Args:
        website: Complete URL (e.g., "https://www.example.edu/page")
        
    Returns:
        str: Clean domain (e.g., "example.edu") or empty string if invalid
    """
    if not website:
        return ""
    
    try:
        domain = re.sub(r'^https?://', '', website)
        domain = re.sub(r'^www\.', '', domain)
        domain = domain.split('/')[0]
        domain = domain.split(':')[0]
        
        if '.' not in domain:
            logger.warning(f"⚠️  Invalid domain format (no TLD): {website}")
            return ""
        
        if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$', domain):
            logger.warning(f"⚠️  Invalid domain format (invalid characters): {website}")
            return ""
        
        return domain
    except Exception as e:
        logger.warning(f"⚠️  Error extracting domain from '{website}': {e}")
        return ""


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
        if not name or str(name).strip() == "":
            return {
                "success": False,
                "formatted_result": "❌ ERROR: Institution name is required",
                "error": "Institution name is required"
            }
        
        name = str(name).strip()
        
        logger.info(f"🔍 Starting TWO-PHASE search for: {name}")
        
        logger.info("   Phase 1/2: Gathering information (OpenAI)...")
        phase1_result = _phase1_exploratory_search(name, country, website)
        
        if not phase1_result["success"]:
            return {
                "success": False,
                "formatted_result": f"❌ ERROR in Phase 1: {phase1_result['error']}",
                "error": phase1_result["error"]
            }
        
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
# PHASE 2 (AUTO-DECISION): STRUCTURED YES/NO DECISION (AWS Bedrock Claude)
# ============================================================================

def _phase2_auto_decision(
    institution_name: str,
    raw_content: str,
    sources: list,
    model_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Phase 2 (Auto-Decision mode): Analyze gathered information and return a
    structured YES/NO decision for CGIAR partnership eligibility.
    Uses AWS Bedrock Claude (rules-validation model, configurable via
    BEDROCK_RULES_MODEL_ID — defaults to Claude Sonnet 4.5, unchanged behavior).

    Returns:
        dict: {
            "approved": bool,
            "confidence": "high" | "medium" | "low",
            "institution_name": str,
            "institution_type": str,
            "is_legal_entity": bool | None,
            "has_research_mandate": bool | None,
            "reason": str,
            "summary": str
        }
    """
    model_id = model_id or os.getenv("BEDROCK_RULES_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
    try:
        sources_text = "\n".join([f"- {url}" for url in sources[:10]]) if sources else "No sources available"

        prompt = f"""You are evaluating whether an institution qualifies as a CGIAR partner based on web search information.

INSTITUTION SEARCHED: {institution_name}

INFORMATION GATHERED FROM WEB SEARCH:
{raw_content}

SOURCES CONSULTED:
{sources_text}

CGIAR PARTNERSHIP ELIGIBILITY CRITERIA:
1. The institution must be a legal entity (or formally affiliated with one that can sign contracts).
2. It must belong to one of these recognized types:
   - University or academic institution
   - National/local research institution
   - International/regional research institution
   - Government entity (ministry, department, agency)
   - Bilateral development agency (e.g., USAID, DFID, GIZ)
   - International/regional financial institution (e.g., World Bank, IDB)
   - UN entity or international organization
   - NGO (with legal registration)
   - Private company (with legal registration)
3. Sub-departments, units, or divisions WITHOUT independent legal status must be REJECTED.
   They may request partnership through their parent organization instead.

DECISION RULES:
- APPROVE (true): Institution is a recognized legal entity of an eligible type.
- REJECT (false): It is a non-independent sub-unit or department, does not exist,
  cannot be verified online, or clearly does not meet the criteria above.
- When available information is very limited or contradictory, lean toward REJECT with low confidence.

Analyze the information and respond ONLY with a valid JSON object. No markdown fences, no extra text:
{{
  "approved": true or false,
  "confidence": "high" or "medium" or "low",
  "institution_name": "Official name found or original name if not found",
  "institution_type": "Most specific CGIAR category that applies",
  "is_legal_entity": true, false, or null,
  "has_research_mandate": true, false, or null,
  "reason": "Clear 1-2 sentence explanation of the decision",
  "summary": "Brief 1-2 sentence description of the institution"
}}"""

        response = bedrock_client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            })
        )

        response_body = json.loads(response['body'].read())
        raw_text = response_body['content'][0]['text'].strip()

        if raw_text.startswith("```"):
            raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text)
            raw_text = re.sub(r'\s*```$', '', raw_text.strip()).strip()

        logger.info(f"Auto-decision raw response: {raw_text}")

        decision_data = json.loads(raw_text)

        return {
            "approved": bool(decision_data.get("approved", False)),
            "confidence": decision_data.get("confidence", "low"),
            "institution_name": decision_data.get("institution_name", institution_name),
            "institution_type": decision_data.get("institution_type", ""),
            "is_legal_entity": decision_data.get("is_legal_entity"),
            "has_research_mandate": decision_data.get("has_research_mandate"),
            "reason": decision_data.get("reason", ""),
            "summary": decision_data.get("summary", "")
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse auto-decision JSON: {e}. Raw text: {raw_text if 'raw_text' in dir() else 'N/A'}")
        return {
            "approved": False,
            "confidence": "low",
            "institution_name": institution_name,
            "institution_type": "",
            "is_legal_entity": None,
            "has_research_mandate": None,
            "reason": "Could not parse analysis result. Manual review required.",
            "summary": ""
        }
    except Exception as e:
        logger.error(f"Phase 2 auto-decision error: {str(e)}")
        return {
            "approved": False,
            "confidence": "low",
            "institution_name": institution_name,
            "institution_type": "",
            "is_legal_entity": None,
            "has_research_mandate": None,
            "reason": f"Analysis failed: {str(e)}",
            "summary": ""
        }


# ============================================================================
# AUTO-DECISION SEARCH FUNCTION (Coordinates Phase 1 + Phase 2 Auto-Decision)
# ============================================================================

def search_institution_auto_decision(
    name: str,
    country: Optional[str] = None,
    website: Optional[str] = None,
    model_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    TWO-PHASE search that returns a structured YES/NO eligibility decision for
    automated CGIAR partner request processing. Does NOT use the narrative
    formatting of search_institution_online — returns structured JSON instead.

    Phase 1: Exploratory search (OpenAI gpt-5-mini) — gather all available info.
    Phase 2: Auto-decision (AWS Bedrock Claude, rules-validation model) — structured YES/NO.

    Args:
        name: Institution name (required)
        country: Country hint (optional, improves search accuracy)
        website: Official website (optional, enables focused domain search)
        model_id: Optional Bedrock model override (defaults to BEDROCK_RULES_MODEL_ID / Sonnet 4.5)

    Returns:
        dict: {
            "success": bool,
            "approved": bool | None,
            "confidence": "high" | "medium" | "low",
            "institution_name": str,
            "institution_type": str,
            "is_legal_entity": bool | None,
            "has_research_mandate": bool | None,
            "reason": str,
            "summary": str,
            "error": str | None
        }
    """
    _empty = {
        "success": False,
        "approved": None,
        "confidence": "low",
        "institution_name": name or "",
        "institution_type": "",
        "is_legal_entity": None,
        "has_research_mandate": None,
        "reason": "",
        "summary": "",
        "error": None
    }

    try:
        if not name or str(name).strip() == "":
            return {**_empty, "reason": "Institution name is required.", "error": "Institution name is required"}

        name = str(name).strip()
        logger.info(f"🤖 Starting AUTO-DECISION search for: {name}")

        logger.info("   Phase 1/2: Gathering information (OpenAI)...")
        phase1_result = _phase1_exploratory_search(name, country, website)

        if not phase1_result["success"]:
            return {
                **_empty,
                "institution_name": name,
                "reason": f"Web search failed: {phase1_result['error']}",
                "error": phase1_result["error"]
            }

        logger.info("   Phase 2/2: Making auto-decision (Claude rules-validation model)...")
        decision = _phase2_auto_decision(
            institution_name=name,
            raw_content=phase1_result["raw_content"],
            sources=phase1_result["sources"],
            model_id=model_id
        )

        verdict = "APPROVED" if decision["approved"] else "REJECTED"
        logger.info(f"🤖 Auto-decision: {verdict} ({decision['confidence']} confidence) — {name}")

        return {
            "success": True,
            "approved": decision["approved"],
            "confidence": decision["confidence"],
            "institution_name": decision["institution_name"],
            "institution_type": decision["institution_type"],
            "is_legal_entity": decision["is_legal_entity"],
            "has_research_mandate": decision["has_research_mandate"],
            "reason": decision["reason"],
            "summary": decision["summary"],
            "error": None
        }

    except Exception as e:
        logger.error(f"Auto-decision search error for '{name}': {str(e)}")
        return {**_empty, "institution_name": name, "reason": f"Processing error: {str(e)}", "error": str(e)}


# ============================================================================
# SAME-INSTITUTION CHECK (duplicate confirmation, small/fast model)
# ============================================================================

def _phase_same_institution_check(
    requester: Dict[str, Any],
    candidate: Dict[str, Any],
    model_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Single-call comparison (no web search) deciding whether the requester's
    submitted institution and a CLARISA hybrid-search candidate are the same
    real-world institution. Uses a smaller/faster Bedrock model than the
    rules-validation Phase 2, since this is a simpler classification task and
    is only run for Very Good / Good matches where latency matters.

    Args:
        requester: dict with whatever of name/acronym/website/institution_type/country
                    the requester submitted (missing fields are simply omitted from the prompt)
        candidate: dict with the CLARISA candidate's name/acronym/website/institution_type/countries
        model_id: Optional Bedrock model override (defaults to BEDROCK_DUPLICATE_CHECK_MODEL_ID)

    Returns:
        dict: {"same_institution": bool, "confidence": "high"|"medium"|"low", "reason": str}
    """
    model_id = model_id or os.getenv("BEDROCK_DUPLICATE_CHECK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")

    def _fmt(fields: Dict[str, Any]) -> str:
        lines = []
        for label, value in fields.items():
            if value:
                lines.append(f"- {label}: {value}")
        return "\n".join(lines) if lines else "- (no additional data provided)"

    requester_block = _fmt({
        "Name": requester.get("name"),
        "Acronym": requester.get("acronym"),
        "Website": requester.get("website"),
        "Institution type": requester.get("institution_type"),
        "Country": requester.get("country"),
    })

    candidate_countries = candidate.get("countries")
    candidate_block = _fmt({
        "Name": candidate.get("name"),
        "Acronym": candidate.get("acronym"),
        "Website": candidate.get("website"),
        "Institution type": candidate.get("institution_type"),
        "Country/Countries": ", ".join(candidate_countries) if isinstance(candidate_countries, list) else candidate_countries,
    })

    prompt = f"""You are comparing two institution records to decide if they refer to the SAME real-world institution.

REQUESTER SUBMITTED DATA (new partner request):
{requester_block}

CLARISA CANDIDATE (existing record found by search):
{candidate_block}

INSTRUCTIONS:
- Treat spelling variations, translations, legal-form suffixes (e.g. "Inc.", "Ltd.", "Foundation"),
  and acronym differences as the SAME institution if the underlying organization is clearly identical.
- Treat them as DIFFERENT institutions if there is a real distinguishing difference: different country
  of headquarters, a parent/sub-unit or affiliate relationship, a different mandate/sector, or simply
  not enough overlap to conclude they are the same entity.
- When the evidence is genuinely ambiguous, prefer "same_institution": false with "confidence": "low"
  — a false negative here only triggers additional verification, while a false positive skips it entirely.

Respond ONLY with a valid JSON object. No markdown fences, no extra text:
{{
  "same_institution": true or false,
  "confidence": "high" or "medium" or "low",
  "reason": "Clear 1-2 sentence explanation of the decision"
}}"""

    try:
        response = bedrock_client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}]
            })
        )

        response_body = json.loads(response['body'].read())
        raw_text = response_body['content'][0]['text'].strip()

        if raw_text.startswith("```"):
            raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text)
            raw_text = re.sub(r'\s*```$', '', raw_text.strip()).strip()

        logger.info(f"Same-institution check raw response: {raw_text}")

        decision_data = json.loads(raw_text)

        return {
            "same_institution": bool(decision_data.get("same_institution", False)),
            "confidence": decision_data.get("confidence", "low"),
            "reason": decision_data.get("reason", "")
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse same-institution check JSON: {e}")
        return {
            "same_institution": False,
            "confidence": "low",
            "reason": "Could not parse comparison result — escalating to full validation."
        }
    except Exception as e:
        logger.error(f"Same-institution check error: {str(e)}")
        return {
            "same_institution": False,
            "confidence": "low",
            "reason": f"Comparison failed ({str(e)}) — escalating to full validation."
        }


def check_same_institution(
    requester_metadata: Dict[str, Any],
    candidate_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Public entry point for the same-institution duplicate check.

    On any error or parse failure, defaults to same_institution=False —
    an error must only cause MORE verification (fall through to full
    web-search + rules validation), never cause an auto-reject by itself.

    Returns:
        dict: {
            "success": bool,
            "same_institution": bool | None,
            "confidence": "high" | "medium" | "low",
            "reason": str,
            "error": str | None
        }
    """
    try:
        result = _phase_same_institution_check(requester_metadata, candidate_metadata)
        return {
            "success": True,
            "same_institution": result["same_institution"],
            "confidence": result["confidence"],
            "reason": result["reason"],
            "error": None
        }
    except Exception as e:
        logger.error(f"check_same_institution error: {str(e)}")
        return {
            "success": False,
            "same_institution": False,
            "confidence": "low",
            "reason": f"Comparison failed ({str(e)}) — escalating to full validation.",
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
    
    if result["success"]:
        logger.info("\n" + result["formatted_result"])
    else:
        logger.error(f"\n❌ Search failed: {result['error']}")
    
    return result
