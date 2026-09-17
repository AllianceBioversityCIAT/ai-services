"""
Pydantic models for the W3/Bilateral AI quality check (P2-3150).

Mirrors contract v0.1 agreed with the Reporting Tool team.
Separate from app/api/models.py so /api/prms-qa is untouched.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class Verdict(str, Enum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"
    GREY = "grey"


class CheckStatus(str, Enum):
    """AC6/AC7: the Reporting Tool must be able to record that a result was
    submitted without a complete quality check."""
    COMPLETED = "completed"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


# --------------------------------------------------------------------------- #
# Request
# --------------------------------------------------------------------------- #

class ResultHeader(BaseModel):
    type: str = Field(..., examples=["Innovation development"])
    reporting_phase: Optional[str] = Field(None, examples=["Reporting 2026"])
    reporting_center: Optional[str] = Field(None, examples=["AfricaRice"])
    primary_science_program: Optional[str] = Field(None, examples=["Sustainable Farming"])


class GeneralInformation(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    result_level: Optional[str] = Field(None, examples=["Output"])
    lead_contact_person: Optional[str] = None


class Project(BaseModel):
    title: Optional[str] = None
    funder: Optional[str] = None


class ExternalPartner(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    role: Optional[str] = None


class TheoryOfChange(BaseModel):
    planned: Optional[bool] = None
    level: Optional[str] = None
    result: Optional[str] = None
    indicator: Optional[str] = None
    contribution: Optional[str] = None
    why_reported: Optional[str] = None


class ContributorsAndPartners(BaseModel):
    lead_center: Optional[str] = None
    contributing_centers: List[str] = Field(default_factory=list)
    lead_project: Optional[Project] = None
    contributing_projects: List[Project] = Field(default_factory=list)
    external_partners: List[ExternalPartner] = Field(default_factory=list)
    no_external_partners: Optional[bool] = None
    theory_of_change: Optional[TheoryOfChange] = None


class GeographicLocation(BaseModel):
    scope: Optional[str] = Field(None, examples=["National"])
    regions: List[str] = Field(default_factory=list)
    countries: List[str] = Field(default_factory=list)
    sub_national: List[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    description: Optional[str] = None
    link: Optional[str] = None
    source: Optional[str] = Field(None, examples=["url", "prms_repository"])
    visibility: Optional[str] = Field(None, examples=["public", "private"])
    tags: List[str] = Field(default_factory=list)

    @property
    def is_evaluable(self) -> bool:
        """Private repository items carry no link and are never scraped -> grey."""
        return bool(self.link) and self.visibility != "private"


class ImpactArea(BaseModel):
    """Optional in bilateral results. When the list is absent or empty the impact
    area criteria are omitted from the assessment - not shown, not penalised.

    Sibling of `sections`, not nested inside it (contract v0.2).
    """
    name: Optional[str] = Field(None, examples=["Gender equality, youth and social inclusion"])
    score: Optional[str] = Field(None, examples=["2 — Principal"])
    subcomponents: List[str] = Field(default_factory=list, examples=[["Youth"]])


class TypeSpecific(BaseModel):
    type: Optional[str] = Field(None, examples=["innovation_development"])
    fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="Display label -> display value, as shown in the form.",
        examples=[{"Innovation typology": "Technological", "Readiness level": "Level 6 — …"}],
    )


class Sections(BaseModel):
    general_information: GeneralInformation = Field(default_factory=GeneralInformation)
    contributors_and_partners: ContributorsAndPartners = Field(
        default_factory=ContributorsAndPartners
    )
    geographic_location: GeographicLocation = Field(default_factory=GeographicLocation)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    type_specific: TypeSpecific = Field(default_factory=TypeSpecific)


class Constraints(BaseModel):
    timeout_seconds: Optional[int] = Field(60, examples=[60])


class QualityAssessmentRequest(BaseModel):
    contract_version: str = Field("0.2", examples=["0.2"])
    request_id: str
    result: ResultHeader
    sections: Sections
    impact_areas: List[ImpactArea] = Field(default_factory=list)
    constraints: Constraints = Field(default_factory=Constraints)
    user_id: Optional[str] = Field(
        None,
        description="User identifier, used to track the interaction for analytics.",
        examples=["user123"],
    )


# --------------------------------------------------------------------------- #
# Response
# --------------------------------------------------------------------------- #

class Coverage(BaseModel):
    """How much of the check actually ran. Lets a caller tell a green backed by a
    full review apart from one where most criteria were never evaluated."""
    criteria_total: int = 0
    criteria_evaluated: int = 0


class OverallVerdict(BaseModel):
    verdict: Verdict
    score: Optional[int] = Field(None, ge=0, le=100)
    summary: str = ""


class SectionVerdict(BaseModel):
    verdict: Verdict
    score: Optional[int] = Field(None, ge=0, le=100)
    comments: str = ""
    strengths: List[str] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)


class EvidenceVerdict(BaseModel):
    index: int
    verdict: Verdict
    reason: str = ""


class SectionVerdicts(BaseModel):
    general_information: SectionVerdict
    contributors_and_partners: SectionVerdict
    geographic_location: SectionVerdict
    evidence: SectionVerdict
    type_specific: SectionVerdict


class QualityAssessmentResponse(BaseModel):
    request_id: str
    criteria_version: str = Field("QA-2026-v1", examples=["QA-2026-v1"])
    overall: OverallVerdict
    sections: SectionVerdicts
    evidence: List[EvidenceVerdict] = Field(default_factory=list)
    # Additive to contract v0.1 — required by AC6/AC7 so the Reporting Tool can
    # record that a result was submitted without a complete check.
    # Both mandatory in the response (contract v0.2).
    status: CheckStatus = CheckStatus.COMPLETED
    degraded_reason: Optional[str] = None
    coverage: Coverage = Field(default_factory=Coverage)
    interaction_id: Optional[str] = Field(
        None, description="Interaction tracking id, when a user_id was supplied."
    )
