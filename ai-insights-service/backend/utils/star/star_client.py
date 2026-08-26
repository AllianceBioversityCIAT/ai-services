import requests
from typing import Any, Optional
from utils.logger.logger_util import get_logger
from utils.config.config_util import STAR_API_BASE_URL, STAR_API_TOKEN

logger = get_logger()

INDICATOR_TYPES: dict[int, dict[str, str]] = {
    1: {
        "name": "Capacity Sharing for Development",
        "description": (
            "Number of individuals trained or engaged by Alliance staff, aiming to lead "
            "to behavioral changes in knowledge, attitude, skills, and practice among "
            "CGIAR and non-CGIAR personnel."
        ),
    },
    2: {
        "name": "Innovation Development",
        "description": (
            "A new, improved, or adapted output or groups of outputs such as technologies, "
            "products and services, policies, and other organizational and institutional "
            "arrangements with high potential to contribute to positive impacts when "
            "used at scale."
        ),
    },
    3: {
        "name": "Knowledge Product",
        "description": (
            "Knowledge products are intellectual assets generated from research and "
            "development activities such as articles, briefs, reports, extension and "
            "training content, databases, software, and multimedia elements that "
            "contribute to behavioral changes in particular actors."
        ),
    },
    4: {
        "name": "Policy Change",
        "description": (
            "Policies, strategies, legal instruments, programs, budgets, or investments "
            "at different scales (local to global) that have been modified in design or "
            "implementation, with evidence that the change was informed by Alliance research."
        ),
    },
    5: {
        "name": "Outcome Impact Case Report (OICR)",
        "description": (
            "An evidence-based report detailing any outcome or impact that has resulted "
            "from the work of one or more CGIAR programs, initiatives, or centers. "
            "Outcome impact case reports must cite robust evidence to demonstrate the "
            "contribution of the CGIAR entity's research findings or innovations to the "
            "outcome or impact. They are used to demonstrate results to funders."
        ),
    },
    6: {
        "name": "Innovation Use",
        "description": (
            "A metric used to assess the extent to which an innovation is already being "
            "used, by which type of users and under which conditions, with a scale ranging "
            "from no use (lowest level) to common use (highest level)."
        ),
    },
}

REQUEST_TIMEOUT_SECONDS = 30


class StarClient:
    """Client for fetching project and results metadata from STAR APIs."""

    def __init__(
        self,
        base_url: Optional[str] = STAR_API_BASE_URL,
        token: Optional[str] = None,
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.token = (token or STAR_API_TOKEN or "").strip()

    def is_configured(self) -> bool:
        return bool(self.base_url)

    def has_auth(self) -> bool:
        return bool(self.token)

    def _auth_headers(self) -> dict[str, str]:
        if not self.token:
            return {}
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _get(self, url: str, params: Optional[dict[str, str]] = None) -> Optional[requests.Response]:
        if not self.is_configured():
            logger.warning("STAR_API_BASE_URL is not configured — skipping STAR API call")
            return None

        if not self.has_auth():
            logger.warning("No STAR access token provided — skipping STAR API call")
            return None

        return requests.get(
            url,
            params=params,
            headers=self._auth_headers(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

    def fetch_project_info(self, contract_id: str) -> Optional[dict[str, Any]]:
        url = f"{self.base_url}/api/agresso/contracts/{contract_id.lower()}/results/count"
        logger.info(f"🌐 Fetching STAR project info from {url}")

        try:
            response = self._get(url)
            if response is None:
                return None
            response.raise_for_status()
            payload = response.json()
            return payload.get("data")
        except requests.exceptions.RequestException as error:
            logger.error(f"Failed to fetch STAR project info for {contract_id}: {error}")
            return None

    def fetch_project_results(self, contract_id: str) -> Optional[list[dict[str, Any]]]:
        url = f"{self.base_url}/api/results"
        params = {"filter-primary-contract": contract_id.lower()}
        logger.info(f"🌐 Fetching STAR project results from {url} (contract={contract_id})")

        try:
            response = self._get(url, params=params)
            if response is None:
                return None
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data")
            return data if isinstance(data, list) else []
        except requests.exceptions.RequestException as error:
            logger.error(f"Failed to fetch STAR project results for {contract_id}: {error}")
            return None


def simplify_project_data(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract the project fields relevant for AI context."""
    sdgs = []
    for sdg in raw.get("sdgs") or []:
        sdgs.append({
            "full_name": sdg.get("full_name"),
            "description": sdg.get("description"),
            "financial_code": sdg.get("financial_code"),
        })

    return {
        "description": raw.get("description"),
        "donor": raw.get("donor"),
        "unit": raw.get("unit"),
        "sdgs": sdgs,
    }


def simplify_results_data(raw_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract the result fields relevant for AI context."""
    simplified = []
    for result in raw_results:
        indicator_id = result.get("indicator_id")
        indicator = INDICATOR_TYPES.get(indicator_id, {})
        simplified.append({
            "title": result.get("title"),
            "description": result.get("description"),
            "indicator_id": indicator_id,
            "indicator_name": indicator.get("name"),
            "indicator_description": indicator.get("description"),
        })
    return simplified


def format_project_context(project_data: dict[str, Any]) -> str:
    """Format project metadata as a prompt section."""
    lines = [
        "Information about this project:",
        f"Description: {project_data.get('description') or 'Not available'}",
        f"Donor: {project_data.get('donor') or 'Not available'}",
        f"Unit: {project_data.get('unit') or 'Not available'}",
    ]

    sdgs = project_data.get("sdgs") or []
    if sdgs:
        lines.append("SDGs this project contributes to:")
        for sdg in sdgs:
            code = sdg.get("financial_code") or "SDG"
            name = sdg.get("full_name") or "Unknown"
            description = sdg.get("description") or "No description available"
            lines.append(f"- {code} ({name}): {description}")
    else:
        lines.append("SDGs this project contributes to: Not available")

    return "\n".join(lines)


def format_results_context(results: list[dict[str, Any]]) -> str:
    """Format project results metadata as a prompt section."""
    lines = [
        "The results that are part of this project have the following characteristics:",
    ]

    if not results:
        lines.append("No results metadata was returned for this project.")
        return "\n".join(lines)

    for index, result in enumerate(results, start=1):
        indicator_id = result.get("indicator_id")
        indicator_name = result.get("indicator_name") or "Unknown indicator"
        indicator_description = result.get("indicator_description") or "No description available"

        lines.extend([
            "",
            f"Result {index}:",
            # f"  Indicator ({indicator_id}): {indicator_name}",
            # f"  Indicator description: {indicator_description}",
            f"  Title: {result.get('title') or 'Not available'}",
            f"  Description: {result.get('description') or 'Not available'}",
        ])

    return "\n".join(lines)


def contract_id_from_project_folder(project_folder: str) -> str:
    """The STAR contract ID is the last segment of the project folder path."""
    return project_folder.strip("/").rsplit("/", 1)[-1]


def fetch_star_context(
    contract_id: str,
    token: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    """
    Fetch and format STAR project info and results for LLM context.

    Returns:
        Tuple of (project_context_text, results_context_text).
        Each value is None when the corresponding fetch fails or returns no data.
    """
    client = StarClient(token=token)
    if not client.is_configured() or not client.has_auth():
        return None, None

    raw_project = client.fetch_project_info(contract_id)
    raw_results = client.fetch_project_results(contract_id)

    project_context = None
    if raw_project:
        project_context = format_project_context(simplify_project_data(raw_project))
        logger.info(f"✅ STAR project context prepared for contract {contract_id}")
    else:
        logger.warning(f"No STAR project info available for contract {contract_id}")

    results_context = None
    if raw_results is not None:
        results_context = format_results_context(simplify_results_data(raw_results))
        logger.info(
            f"✅ STAR results context prepared for contract {contract_id} "
            f"({len(raw_results)} result(s))"
        )
    else:
        logger.warning(f"No STAR results metadata available for contract {contract_id}")

    return project_context, results_context


star_client = StarClient()
