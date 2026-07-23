import re
from typing import Annotated, Any, List, Optional, Union, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from app.llm.shared.cgiar_centers import normalize_cgiar_center_ref
from app.schemas.prms_innovation_reference import (
    normalize_innovation_typology_ref,
    normalize_innovation_readiness_level_ref,
)
from app.schemas.prms_innovation_use_reference import (
    INSTITUTION_TYPE_OTHER_ID,
    normalize_innovation_use_actor_ref,
    normalize_innovation_use_measure_ref,
    normalize_innovation_use_organization_ref,
    resolve_institution_type,
)
from app.schemas.prms_policy_reference import (
    normalize_implementing_organization_ref,
    normalize_policy_stage_ref,
    normalize_policy_type_ref,
    resolve_status_amount,
)


# --- MDS bilateral models (pilot: common + capacity_sharing) ---


class InstitutionRef(BaseModel):
    """contributing_partners item (non-CGIAR institutions)."""
    model_config = ConfigDict(exclude_none=True)

    institution_id: Optional[int] = Field(None, description="CLARISA institution id")
    acronym: Optional[str] = Field(None, description="Institution acronym")
    name: Optional[str] = Field(None, description="Institution name")

    @model_validator(mode="after")
    def require_partner_identity(self):
        if not any([
            self.institution_id is not None,
            self.acronym and self.acronym.strip(),
            self.name and self.name.strip(),
        ]):
            raise ValueError("contributing partner requires institution_id, acronym, or name")
        return self

    @field_validator("name", "acronym", mode="before")
    @classmethod
    def strip_text(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return str(v).strip()

class CgiarCenterRef(BaseModel):
    """lead_center / contributing_center — must match PRMS CGIAR center catalog."""
    model_config = ConfigDict(exclude_none=True)

    institution_id: int = Field(..., description="CGIAR center institution id")
    acronym: str = Field(..., description="CGIAR center acronym")
    name: str = Field(..., description="CGIAR center name")

    @model_validator(mode="before")
    @classmethod
    def resolve_from_catalog(cls, data: Any):
        resolved = normalize_cgiar_center_ref(data)
        if not resolved:
            raise ValueError("unknown CGIAR center")
        return resolved


class GeoRegionRef(BaseModel):
    model_config = ConfigDict(exclude_none=True)

    um49code: int = Field(..., description="UN M49 region code")


class GeoCountryRef(BaseModel):
    model_config = ConfigDict(exclude_none=True)

    id: Optional[int] = Field(None, description="CLARISA country id")
    iso_alpha_2: Optional[str] = Field(None, description="ISO Alpha-2 country code")
    iso_alpha_3: Optional[str] = Field(None, description="ISO Alpha-3 code")
    subnational_areas: Optional[List[str]] = Field(
        None,
        description="ISO 3166-2 subnational area codes when scope is Sub-national",
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_country_shape(cls, data: Any):
        if not isinstance(data, dict):
            return data
        normalized = dict(data)

        legacy_code = normalized.pop("code", None)
        if legacy_code and not normalized.get("iso_alpha_2"):
            normalized["iso_alpha_2"] = legacy_code

        legacy_areas = normalized.pop("areas", None)
        if legacy_areas and not normalized.get("subnational_areas"):
            normalized["subnational_areas"] = legacy_areas

        normalized.pop("code", None)
        normalized.pop("areas", None)
        return normalized

    @field_validator("iso_alpha_2", mode="before")
    @classmethod
    def normalize_iso2(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return str(v).strip().upper()

    @field_validator("iso_alpha_3", mode="before")
    @classmethod
    def normalize_iso3(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return str(v).strip().upper()

    @field_validator("subnational_areas", mode="before")
    @classmethod
    def normalize_subnational_areas(cls, v):
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError("subnational_areas must be an array of ISO 3166-2 codes")
        normalized = [str(item).strip().upper() for item in v if str(item).strip()]
        return normalized or None

    @model_validator(mode="after")
    def require_country_identity(self):
        if self.subnational_areas:
            if not self.iso_alpha_2:
                raise ValueError("iso_alpha_2 is required when subnational_areas is present")
            if not self.subnational_areas:
                raise ValueError("subnational_areas must contain at least one ISO 3166-2 code")
            return self
        if not any([self.id is not None, self.iso_alpha_2, self.iso_alpha_3]):
            raise ValueError("country requires id, iso_alpha_2, or iso_alpha_3")
        return self


GEO_FOCUS_SCOPE_LABEL_TO_CODE = {
    "Global": 1,
    "Regional": 2,
    "National": 4,
    "Sub-national": 5,
    "This is yet to be determined": 50,
}
GEO_FOCUS_SCOPE_CODE_TO_LABEL = {
    code: label for label, code in GEO_FOCUS_SCOPE_LABEL_TO_CODE.items()
}


class GeoFocus(BaseModel):
    model_config = ConfigDict(exclude_none=True)

    scope_code: Optional[int] = Field(None, description="PRMS geo scope code")
    scope_label: Optional[str] = Field(None, description="PRMS geo scope label")
    regions: Optional[List[GeoRegionRef]] = Field(None, description="Regions when Regional")
    countries: Optional[List[GeoCountryRef]] = Field(
        None,
        description="Countries when National/Sub-national; Sub-national items use iso_alpha_2 + subnational_areas",
    )

    @field_validator("scope_label")
    @classmethod
    def validate_scope_label(cls, v):
        if v is None:
            return v
        if v not in GEO_FOCUS_SCOPE_LABEL_TO_CODE:
            return "This is yet to be determined"
        return v

    @model_validator(mode="after")
    def sync_scope_code_and_label(self):
        if self.scope_label:
            self.scope_code = GEO_FOCUS_SCOPE_LABEL_TO_CODE[self.scope_label]
        elif self.scope_code in GEO_FOCUS_SCOPE_CODE_TO_LABEL:
            self.scope_label = GEO_FOCUS_SCOPE_CODE_TO_LABEL[self.scope_code]
        elif self.scope_code is None and self.scope_label is None:
            return self
        else:
            self.scope_label = "This is yet to be determined"
            self.scope_code = 50
        return self

    @model_validator(mode="after")
    def enforce_scope_shape(self):
        label = self.scope_label
        if label == "Global":
            self.regions = None
            self.countries = None
        elif label == "Regional":
            self.countries = None
        elif label == "National":
            self.regions = None
            if self.countries:
                self.countries = [
                    country.model_copy(update={"subnational_areas": None})
                    for country in self.countries
                ]
        elif label == "Sub-national":
            self.regions = None
        return self


class EvidenceItem(BaseModel):
    model_config = ConfigDict(exclude_none=True)

    link: str = Field(..., description="Evidence URI")
    description: Optional[str] = Field(None, description="Evidence description")

    @field_validator("link")
    @classmethod
    def validate_link(cls, v):
        if not v or (isinstance(v, str) and not v.strip()):
            raise ValueError("link is required")
        return v.strip()


class NumberPeopleTrained(BaseModel):
    model_config = ConfigDict(exclude_none=True)

    women: Optional[int] = None
    men: Optional[int] = None
    non_binary: Optional[int] = None
    unknown: Optional[int] = None

    @field_validator("women", "men", "non_binary", "unknown", mode="before")
    @classmethod
    def validate_counts(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and v.isdigit():
            v = int(v)
        if isinstance(v, int) and v >= 0:
            return v
        return None

    @model_validator(mode="after")
    def require_at_least_one_count(self):
        if not any(value is not None for value in (self.women, self.men, self.non_binary, self.unknown)):
            raise ValueError("number_people_trained requires at least one gender count")
        return self


class CapacitySharingBlock(BaseModel):
    model_config = ConfigDict(exclude_none=True)

    number_people_trained: Optional[NumberPeopleTrained] = None
    length_training: Optional[str] = Field(None, description="Short-term | Long-term")
    delivery_method: Optional[str] = Field(
        None,
        description="Virtual / Online | In person | Blended (in-person and virtual)",
    )

    @field_validator("length_training")
    @classmethod
    def validate_length_training(cls, v):
        if v is None:
            return v
        valid = {"Short-term", "Long-term"}
        return v if v in valid else None

    @field_validator("delivery_method")
    @classmethod
    def validate_delivery_method(cls, v):
        if v is None:
            return v
        valid = {"Virtual / Online", "In person", "Blended (in-person and virtual)"}
        return v if v in valid else None


class MdsBaseResultModel(BaseModel):
    """Common MDS fields for bilateral extracted_mds (pilot indicators)."""
    model_config = ConfigDict(exclude_none=True)

    indicator: str = Field(..., description="Result indicator discriminator")
    title: str = Field(..., description="Result title")
    description: str = Field(..., description="Result description")
    lead_center: Optional[CgiarCenterRef] = None
    geo_focus: Optional[GeoFocus] = None
    contributing_center: Optional[List[CgiarCenterRef]] = None
    contributing_partners: Optional[List[InstitutionRef]] = None
    evidence: Optional[List[EvidenceItem]] = None

    @field_validator("lead_center", mode="before")
    @classmethod
    def normalize_lead_center(cls, v):
        if v is None:
            return None
        resolved = normalize_cgiar_center_ref(v)
        return resolved

    @field_validator("contributing_center", mode="before")
    @classmethod
    def normalize_contributing_centers(cls, v):
        if v is None:
            return None
        if not isinstance(v, list):
            return v
        normalized = []
        for item in v:
            resolved = normalize_cgiar_center_ref(item)
            if resolved:
                normalized.append(resolved)
        return normalized or None

    @field_validator("title", "description")
    @classmethod
    def strip_required_text(cls, v):
        if not v or (isinstance(v, str) and not v.strip()):
            raise ValueError("required text field cannot be empty")
        return v.strip() if isinstance(v, str) else str(v)

    @field_validator("contributing_center", "contributing_partners", "evidence", mode="before")
    @classmethod
    def empty_list_to_none(cls, v):
        if isinstance(v, list) and len(v) == 0:
            return None
        return v


class CapacitySharingResult(MdsBaseResultModel):
    """Capacity Sharing for Development — MDS bilateral shape."""
    indicator: Literal["Capacity Sharing for Development"] = "Capacity Sharing for Development"
    geo_focus: GeoFocus
    capacity_sharing: Optional[CapacitySharingBlock] = None


class PolicyStatusAmountRef(BaseModel):
    model_config = ConfigDict(exclude_none=True)

    id: Optional[int] = None
    name: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def resolve_from_catalog(cls, data: Any):
        if isinstance(data, dict):
            resolved = resolve_status_amount(item_id=data.get("id"), name=data.get("name"))
            if resolved:
                return resolved
        return data

    @model_validator(mode="after")
    def require_id_or_name(self):
        if self.id is None and not self.name:
            raise ValueError("status_amount requires id or name")
        return self


class PolicyTypeRef(BaseModel):
    model_config = ConfigDict(exclude_none=True)

    id: Optional[int] = None
    name: Optional[str] = None
    status_amount: Optional[PolicyStatusAmountRef] = None
    amount: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def resolve_from_catalog(cls, data: Any):
        resolved = normalize_policy_type_ref(data)
        return resolved or data

    @model_validator(mode="after")
    def validate_budget_fields(self):
        if self.id is None and not self.name:
            raise ValueError("policy_type requires id or name")
        if self.id != 1:
            self.status_amount = None
            self.amount = None
        return self


class PolicyStageRef(BaseModel):
    model_config = ConfigDict(exclude_none=True)

    id: Optional[int] = None
    name: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def resolve_from_catalog(cls, data: Any):
        resolved = normalize_policy_stage_ref(data)
        return resolved or data

    @model_validator(mode="after")
    def require_id_or_name(self):
        if self.id is None and not self.name:
            raise ValueError("policy_stage requires id or name")
        return self


class ImplementingOrganizationRef(BaseModel):
    model_config = ConfigDict(exclude_none=True)

    institutions_id: Optional[int] = Field(None, description="Implementing organization id")
    institutions_acronym: Optional[str] = Field(None, description="Implementing organization acronym")
    institutions_name: Optional[str] = Field(None, description="Implementing organization name")

    @model_validator(mode="before")
    @classmethod
    def normalize_shape(cls, data: Any):
        resolved = normalize_implementing_organization_ref(data)
        return resolved or data

    @model_validator(mode="after")
    def require_identity(self):
        if self.institutions_id is None and not self.institutions_acronym and not self.institutions_name:
            raise ValueError(
                "implementing organization requires institutions_id, institutions_acronym, or institutions_name"
            )
        return self


class PolicyChangeBlock(BaseModel):
    model_config = ConfigDict(exclude_none=True)

    policy_type: Optional[PolicyTypeRef] = None
    policy_stage: Optional[PolicyStageRef] = None
    implementing_organization: Optional[List[ImplementingOrganizationRef]] = None

    @field_validator("implementing_organization", mode="before")
    @classmethod
    def normalize_implementing_organizations(cls, value):
        if value is None:
            return None
        if not isinstance(value, list):
            return value
        normalized = []
        for item in value:
            resolved = normalize_implementing_organization_ref(item)
            if resolved:
                normalized.append(resolved)
        return normalized or None


class PolicyChangeResult(MdsBaseResultModel):
    """Policy Change — MDS bilateral shape."""
    indicator: Literal["Policy Change"] = "Policy Change"
    geo_focus: GeoFocus
    policy_change: Optional[PolicyChangeBlock] = None


class InnovationTypologyRef(BaseModel):
    model_config = ConfigDict(exclude_none=True)

    code: Optional[int] = None
    name: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def resolve_from_catalog(cls, data: Any):
        resolved = normalize_innovation_typology_ref(data)
        return resolved or data

    @model_validator(mode="after")
    def require_code_or_name(self):
        if self.code is None and not self.name:
            raise ValueError("innovation_typology requires code or name")
        return self


class InnovationReadinessLevelRef(BaseModel):
    model_config = ConfigDict(exclude_none=True)

    id: Optional[int] = None
    name: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def resolve_from_catalog(cls, data: Any):
        resolved = normalize_innovation_readiness_level_ref(data)
        return resolved or data

    @model_validator(mode="after")
    def require_id_or_name(self):
        if self.id is None and not self.name:
            raise ValueError("innovation_readiness_level requires id or name")
        return self


class InnovationDevelopmentBlock(BaseModel):
    model_config = ConfigDict(exclude_none=True)

    innovation_typology: Optional[InnovationTypologyRef] = None
    innovation_developers: Optional[str] = Field(
        None,
        description=(
            "Innovation developer contact(s): name, email, and organizational affiliation "
            "as a formatted string"
        ),
    )
    innovation_readiness_level: Optional[InnovationReadinessLevelRef] = None

    @field_validator("innovation_developers", mode="before")
    @classmethod
    def strip_developers(cls, value):
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return str(value).strip()


class InnovationDevelopmentResult(MdsBaseResultModel):
    """Innovation Development — MDS bilateral shape."""
    indicator: Literal["Innovation Development"] = "Innovation Development"
    geo_focus: GeoFocus
    innovation_development: Optional[InnovationDevelopmentBlock] = None


class InnovationUseActorRef(BaseModel):
    model_config = ConfigDict(exclude_none=True)

    actor_type_id: Optional[int] = None
    actor_type_name: Optional[str] = None
    other_actor_type: Optional[str] = None
    sex_and_age_disaggregation: Optional[bool] = None
    how_many: Optional[Union[int, str]] = None
    women: Optional[Union[int, str]] = None
    women_youth: Optional[Union[int, str]] = None
    men: Optional[Union[int, str]] = None
    men_youth: Optional[Union[int, str]] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_shape(cls, data: Any):
        resolved = normalize_innovation_use_actor_ref(data)
        return resolved or data

    @model_validator(mode="after")
    def validate_actor_rules(self):
        if self.actor_type_id is None and not self.actor_type_name:
            raise ValueError("actor requires actor_type_id or actor_type_name")
        if self.actor_type_id == 5 and not self.other_actor_type:
            raise ValueError("other_actor_type is required when actor_type_id is 5")
        if self.sex_and_age_disaggregation and self.how_many is None:
            raise ValueError("how_many is required when sex_and_age_disaggregation is true")
        return self


class InnovationUseOrganizationRef(BaseModel):
    model_config = ConfigDict(exclude_none=True)

    organization_type: Optional[str] = None
    institution_types_id: Optional[int] = None
    institution_types_name: Optional[str] = None
    other_institution: Optional[str] = None
    how_many: Optional[Union[int, str]] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_shape(cls, data: Any):
        resolved = normalize_innovation_use_organization_ref(data)
        return resolved or data

    @model_validator(mode="after")
    def validate_organization_rules(self):
        if self.institution_types_id is None:
            raise ValueError("organization requires institution_types_id")
        resolved = resolve_institution_type(item_id=self.institution_types_id)
        if resolved:
            parent_type = resolved.get("organization_type")
            if parent_type:
                if not self.organization_type:
                    raise ValueError(
                        f"organization_type is required when institution_types_id is {self.institution_types_id}"
                    )
                if self.organization_type.strip().lower() != parent_type.lower():
                    raise ValueError(
                        f"organization_type must be {parent_type!r} when institution_types_id is {self.institution_types_id}"
                    )
            elif self.organization_type:
                raise ValueError(
                    f"organization_type must not be set when institution_types_id is {self.institution_types_id}"
                )
        if self.institution_types_id == INSTITUTION_TYPE_OTHER_ID and not self.other_institution:
            raise ValueError("other_institution is required when institution_types_id is 78")
        return self


class InnovationUseMeasureRef(BaseModel):
    model_config = ConfigDict(exclude_none=True)

    unit_of_measure: str
    quantity: Optional[Union[str, int, float]] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_shape(cls, data: Any):
        resolved = normalize_innovation_use_measure_ref(data)
        return resolved or data


class CurrentInnovationUseNumbersBlock(BaseModel):
    model_config = ConfigDict(exclude_none=True)

    innov_use_to_be_determined: bool
    actors: Optional[List[InnovationUseActorRef]] = None
    organization: Optional[List[InnovationUseOrganizationRef]] = None
    measures: Optional[List[InnovationUseMeasureRef]] = None

    @field_validator("actors", mode="before")
    @classmethod
    def normalize_actors(cls, value):
        if value is None:
            return None
        if not isinstance(value, list):
            return value
        normalized = []
        for item in value:
            resolved = normalize_innovation_use_actor_ref(item)
            if resolved:
                normalized.append(resolved)
        return normalized or None

    @field_validator("organization", mode="before")
    @classmethod
    def normalize_organizations(cls, value):
        if value is None:
            return None
        if not isinstance(value, list):
            return value
        normalized = []
        for item in value:
            resolved = normalize_innovation_use_organization_ref(item)
            if resolved:
                normalized.append(resolved)
        return normalized or None

    @field_validator("measures", mode="before")
    @classmethod
    def normalize_measures(cls, value):
        if value is None:
            return None
        if not isinstance(value, list):
            return value
        normalized = []
        for item in value:
            resolved = normalize_innovation_use_measure_ref(item)
            if resolved:
                normalized.append(resolved)
        return normalized or None

    @model_validator(mode="after")
    def validate_use_numbers(self):
        if self.innov_use_to_be_determined:
            self.actors = None
            self.organization = None
            self.measures = None
            return self
        if not any([self.actors, self.organization, self.measures]):
            raise ValueError(
                "when innov_use_to_be_determined is false, "
                "at least one of actors, organization, or measures is required"
            )
        return self


class InnovationUseBlock(BaseModel):
    model_config = ConfigDict(exclude_none=True)

    current_innovation_use_numbers: CurrentInnovationUseNumbersBlock


class InnovationUseResult(MdsBaseResultModel):
    """Innovation Use — MDS bilateral shape."""
    indicator: Literal["Innovation Use"] = "Innovation Use"
    geo_focus: GeoFocus
    innovation_use: Optional[InnovationUseBlock] = None


# Legacy STAR-shaped models (pending MDS migration for other indicators)


class AiRawUser(BaseModel):
    """User information with similarity score for AI matching"""
    model_config = ConfigDict(exclude_none=True)
    
    name: str = Field(..., description="User name")
    code: Optional[str] = Field(None, description="User code")
    similarity_score: float = Field(..., description="Similarity score for matching")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate and clean name"""
        if not v or (isinstance(v, str) and v.strip() == ""):
            raise ValueError("name is required and cannot be empty")
        return v.strip() if isinstance(v, str) else str(v)


class AiRawCountry(BaseModel):
    """Country information with optional subnational areas"""
    model_config = ConfigDict(exclude_none=True)
    
    code: str = Field(..., description="ISO Alpha-2 country code")
    areas: Optional[List[str]] = Field(None, description="ISO 3166-2 subnational area codes")
    
    @field_validator('code')
    @classmethod
    def validate_code(cls, v):
        """Validate and clean country code"""
        if not v or (isinstance(v, str) and v.strip() == ""):
            raise ValueError("code is required and cannot be empty")
        return v.strip().upper() if isinstance(v, str) else str(v).upper()
    
    @field_validator('areas', mode='before')
    @classmethod
    def validate_areas(cls, v):
        """Ensure areas is a list of strings or None"""
        if v is None:
            return None
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [str(area) for area in v if area]
        return None


class BaseResultModel(BaseModel):
    """Base result model with common fields"""
    model_config = ConfigDict(exclude_none=True)
    
    indicator: str = Field(..., description="Type of indicator")
    title: str = Field(..., description="Result title")
    description: str = Field(..., description="Result description")
    keywords: List[str] = Field(..., description="Relevant keywords")
    geoscope_level: str = Field(..., description="Geographic level")
    regions: Optional[List[int]] = Field(None, description="UN49 region codes (only for Regional level)")
    countries: Optional[List[AiRawCountry]] = Field(None, description="Countries with optional subnational areas (for National/Sub-national)")
    main_contact_person: Optional[AiRawUser] = Field(None, description="Main contact person")

    @field_validator('keywords', mode='before')
    @classmethod
    def ensure_keywords_is_list(cls, v):
        """Ensure keywords is always a list"""
        if isinstance(v, str):
            return [v.lower()]
        if isinstance(v, list):
            return [str(keyword).lower() for keyword in v]
        return []
    
    @field_validator('geoscope_level')
    @classmethod
    def validate_geoscope_level(cls, v):
        """Validate geoscope level values"""
        valid_levels = ["Global", "Regional", "National", "Sub-national", "This is yet to be determined"]
        if v not in valid_levels:
            return "This is yet to be determined"
        return v
    
    @field_validator('regions', mode='before')
    @classmethod
    def validate_regions(cls, v):
        """Convert regions to list of integers"""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                v = eval(v)
            except:
                return None
        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, dict) and 'id' in item:
                    result.append(int(item['id']))
                elif isinstance(item, (int, str)):
                    try:
                        result.append(int(item))
                    except:
                        pass
            return result if result else None
        return None
    
    @field_validator('countries', mode='before')
    @classmethod
    def validate_countries(cls, v):
        """Ensure countries is a list of AiRawCountry objects or None"""
        if v is None:
            return None
        if not isinstance(v, list):
            return None
        if len(v) == 0:
            return None
        return v


class InnovationActorModel(BaseModel):
    """Individual actor involved in innovation"""
    model_config = ConfigDict(exclude_none=True)
    
    name: Optional[str] = Field(None, description="Actor name (optional - can be partial entry)")
    type: Optional[str] = Field(None, description="Actor type")
    gender_age: Optional[List[str]] = Field(None, description="Gender and age information (optional)")
    other_actor_type: Optional[str] = Field(None, description="Other actor type if type is 'Other'")

    @field_validator('type')
    @classmethod
    def validate_type(cls, v):
        """Validate actor type values"""
        valid_types = [
            "Farmers / (agro)pastoralist / herders / fishers",
            "Researchers",
            "Extension agents",
            "Policy actors (public or private)",
            "Other"
        ]
        if v and v not in valid_types:
            return "Other"
        return v

    @field_validator('gender_age', mode='before')
    @classmethod
    def ensure_gender_age_is_list(cls, v):
        """Ensure gender_age is always a list or None"""
        if v is None:
            return None
        if isinstance(v, str):
            return [v]
        if not isinstance(v, list):
            return None
        return v
    
    @field_validator('gender_age')
    @classmethod
    def validate_gender_age_values(cls, v):
        """Validate gender_age contains only valid values"""
        if v is None:
            return None
        valid_values = ["Women: Youth", "Women: Non-youth", "Men: Youth", "Men: Non-youth"]
        filtered = [val for val in v if val in valid_values]
        return filtered if filtered else None


class OrganizationModel(BaseModel):
    """Organization involved in innovation"""
    model_config = ConfigDict(exclude_none=True)
    
    institution_name: Optional[str] = Field(None, description="Organization name")
    institution_id: Optional[str] = Field(None, description="Organization ID from mapping service")
    similarity_score: Optional[float] = Field(None, description="Similarity score from mapping")
    type: Optional[str] = Field(None, description="Organization type")
    sub_type: Optional[str] = Field(None, description="Organization subtype")
    other_type: Optional[str] = Field(None, description="Other organization type if type is 'Other'")

    @field_validator('type')
    @classmethod
    def validate_type(cls, v):
        """Validate organization type values"""
        valid_types = [
            "NGO",
            "Research organizations and universities",
            "Organization (other than financial or research)",
            "Government",
            "Financial institution",
            "Private company (other than financial)",
            "Public-Private Partnership",
            "Foundation",
            "Other"
        ]
        if v and v not in valid_types:
            return "Other"
        return v
    
    @model_validator(mode='after')
    def validate_conditional_fields(self):
        """Validate sub_type and other_type based on organization type"""
        org_type = self.type
        sub_type = self.sub_type
        other_type = self.other_type
        
        if other_type:
            if not org_type or org_type != "Other":
                self.other_type = None
        
        if not sub_type:
            return self
        
        if not org_type:
            self.sub_type = None
            return self
        
        valid_subtypes_map = {
            "NGO": [
                "NGO International",
                "NGO International (General)",
                "NGO International (Farmers)",
                "NGO Regional",
                "NGO Regional (General)",
                "NGO Regional (Farmers)",
                "NGO National",
                "NGO National (General)",
                "NGO National (Farmers)",
                "NGO Local",
                "NGO Local (General)",
                "NGO Local (Farmers)"
            ],
            "Research organizations and universities": [
                "Research organizations and universities International",
                "Research organizations and universities International (General)",
                "Research organizations and universities International (Universities)",
                "Research organizations and universities International (CGIAR)",
                "Research organizations and universities Regional",
                "Research organizations and universities Regional (NA)",
                "Research organizations and universities Regional (Universities)",
                "Research organizations and universities National",
                "Research organizations and universities National (NARS)",
                "Research organizations and universities National (Universities)",
                "Research organizations and universities Local",
                "Research organizations and universities Local (NA)",
                "Research organizations and universities Local (Universities)"
            ],
            "Organization (other than financial or research)": [
                "Organization (other than financial or research) International",
                "Organization (other than financial or research) Regional"
            ],
            "Government": [
                "Government (National)",
                "Government (Subnational)"
            ],
            "Financial institution": [
                "Financial Institution",
                "Financial Institution International",
                "Financial Institution Regional",
                "Financial Institution National",
                "Financial Institution Local"
            ]
        }
        
        no_subtype_types = [
            "Private company (other than financial)",
            "Public-Private Partnership",
            "Foundation",
            "Other"
        ]
        
        if org_type in no_subtype_types:
            self.sub_type = None
            return self
        
        if org_type in valid_subtypes_map:
            if sub_type not in valid_subtypes_map[org_type]:
                self.sub_type = None
        
        return self


class OtherOutputResult(MdsBaseResultModel):
    """Other Output — MDS bilateral shape (common fields only)."""
    indicator: Literal["Other Output"] = "Other Output"
    geo_focus: GeoFocus


class OtherOutcomeResult(MdsBaseResultModel):
    """Other Outcome — MDS bilateral shape (common fields only)."""
    indicator: Literal["Other Outcome"] = "Other Outcome"
    geo_focus: GeoFocus


ResultModel = Annotated[
    Union[
        CapacitySharingResult,
        PolicyChangeResult,
        InnovationDevelopmentResult,
        InnovationUseResult,
        OtherOutputResult,
        OtherOutcomeResult,
    ],
    Field(discriminator="indicator"),
]


class MiningResponse(BaseModel):
    """Complete mining response"""
    model_config = ConfigDict(exclude_none=True)
    
    results: List[ResultModel] = Field(..., description="Extracted results from document")
    
    @field_validator('results', mode='before')
    @classmethod
    def ensure_results_list(cls, v):
        """Ensure results is always a list"""
        if not isinstance(v, list):
            return []
        return v


class ErrorResponse(BaseModel):
    """Error response model"""
    status: str = Field("error", description="Status")
    error: str = Field(..., description="Error message")