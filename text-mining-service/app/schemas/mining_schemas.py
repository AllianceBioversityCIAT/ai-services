import re
from datetime import datetime
from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field, field_validator


class GeoscopeModel(BaseModel):
    """Geographical scope information"""
    level: str = Field(..., description="Geographic level")
    sub_list: Optional[List[Union[str, dict]]] = Field(None, description="List of regions/countries or subnational areas")

    @field_validator('level')
    @classmethod
    def validate_level(cls, v):
        """Validate geoscope level values"""
        valid_levels = ["Global", "Regional", "National", "Sub-national", "This is yet to be determined"]
        if v not in valid_levels:
            return "This is yet to be determined"
        return v


class InnovationActorModel(BaseModel):
    """Individual actor involved in innovation"""
    name: str = Field(..., description="Actor name")
    type: str = Field(..., description="Actor type")
    gender_age: List[str] = Field(..., description="Gender and age information")
    other_actor_type: Optional[str] = Field(None, description="Other actor type if type is 'Other'")

    @field_validator('gender_age', mode='before')
    @classmethod
    def ensure_gender_age_is_list(cls, v):
        """Ensure gender_age is always a list"""
        if isinstance(v, str):
            return [v]
        if not isinstance(v, list):
            return []
        return v
    
    @field_validator('gender_age')
    @classmethod
    def validate_gender_age_values(cls, v):
        """Validate gender_age contains only valid values"""
        valid_values = ["Women: Youth", "Women: Non-youth", "Men: Youth", "Men: Non-youth"]
        return [val for val in v if val in valid_values]


# class OrganizationModel(BaseModel):
#     """Organization involved in innovation"""
    # name: str = Field(..., description="Organization name")
    # type: str = Field(..., description="Organization type(s)")
    # sub_type: Optional[str] = Field(None, description="Organization subtype")
    # other_type: Optional[str] = Field(None, description="Other organization type if type is 'Other'")


class BaseResultModel(BaseModel):
    """Base result model with common fields"""
    indicator: str = Field(..., description="Type of indicator")
    title: str = Field(..., description="Result title")
    description: str = Field(..., description="Result description")
    keywords: List[str] = Field(..., description="Relevant keywords")
    geoscope: GeoscopeModel = Field(..., description="Geographical scope")
    alliance_main_contact_person_first_name: str = Field(..., description="Contact first name")
    alliance_main_contact_person_last_name: str = Field(..., description="Contact last name")

    @field_validator('keywords', mode='before')
    @classmethod
    def ensure_keywords_is_list(cls, v):
        """Ensure keywords is always a list"""
        if isinstance(v, str):
            return [v.lower()]
        if isinstance(v, list):
            return [str(keyword).lower() for keyword in v]
        return []
    
    @field_validator('alliance_main_contact_person_first_name', 'alliance_main_contact_person_last_name')
    @classmethod
    def validate_contact_names(cls, v):
        """Set default value for missing contact names"""
        if not v or v.strip() == "":
            return "Not collected"
        return v.strip()


class CapacityDevelopmentResult(BaseResultModel):
    """Capacity Sharing for Development specific fields"""
    indicator: Literal["Capacity Sharing for Development"] = "Capacity Sharing for Development"
    training_type: Optional[str] = Field(None, description="Training type")
    total_participants: Optional[int] = Field(None, description="Total participants count")
    male_participants: Optional[int] = Field(None, description="Male participants count")
    female_participants: Optional[int] = Field(None, description="Female participants count")
    non_binary_participants: Optional[int] = Field(None, description="Non-binary participants count")
    delivery_modality: Optional[str] = Field(None, description="Delivery modality")
    start_date: Optional[str] = Field(None, description="Start date")
    end_date: Optional[str] = Field(None, description="End date")
    length_of_training: Optional[str] = Field(None, description="Training length")
    degree: Optional[str] = Field(None, description="Degree type")

    @field_validator('training_type')
    @classmethod
    def validate_training_type(cls, v):
        """Validate training type values"""
        if v and v not in ["Individual training", "Group training"]:
            return None
        return v
    
    @field_validator('total_participants', 'male_participants', 'female_participants', 'non_binary_participants', mode='before')
    @classmethod
    def validate_participant_counts(cls, v):
        """Convert string numbers to integers and validate non-negative"""
        if v is None or v == "Not collected":
            return None
        if isinstance(v, str) and v.isdigit():
            v = int(v)
        if isinstance(v, int) and v >= 0:
            return v
        return None
    
    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_dates(cls, v):
        """Validate date format (YYYY-MM-DD) or 'Not collected'"""
        if v is None or v == "Not collected":
            return "Not collected"
        if isinstance(v, str) and re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            return v
        return "Not collected"
    
    @field_validator('length_of_training')
    @classmethod
    def validate_training_length(cls, v):
        """Validate training length values"""
        if v and v not in ["Short-term", "Long-term", "Not collected"]:
            return "Not collected"
        return v


class PolicyChangeResult(BaseResultModel):
    """Policy Change specific fields"""
    indicator: Literal["Policy Change"] = "Policy Change"
    policy_type: Optional[str] = Field(None, description="Policy type")
    stage_in_policy_process: Optional[str] = Field(None, description="Policy stage")
    evidence_for_stage: Optional[str] = Field(None, description="Evidence for stage")

    @field_validator('policy_type')
    @classmethod
    def validate_policy_type(cls, v):
        """Validate policy type values"""
        valid_types = ["Policy or Strategy", "Legal instrument", "Program, Budget, or Investment", "Not collected"]
        if v and v not in valid_types:
            return "Not collected"
        return v
    
    @field_validator('stage_in_policy_process')
    @classmethod
    def validate_policy_stage(cls, v):
        """Validate policy stage values"""
        valid_stages = [
            "Stage 1: Research taken up by next user, policy change not yet enacted.",
            "Stage 2: Policy enacted.",
            "Stage 3: Evidence of impact of policy.",
            "Not collected"
        ]
        if v and v not in valid_stages:
            return "Not collected"
        return v


class InnovationDevelopmentResult(BaseResultModel):
    """Innovation Development specific fields"""
    indicator: Literal["Innovation Development"] = "Innovation Development"
    short_title: Optional[str] = Field(None, description="Short title")
    innovation_nature: Optional[str] = Field(None, description="Innovation nature")
    innovation_type: Optional[str] = Field(None, description="Innovation type")
    assess_readiness: Optional[int] = Field(None, description="Readiness assessment")
    anticipated_users: Optional[str] = Field(None, description="Anticipated users")
    innovation_actors_detailed: Optional[List[InnovationActorModel]] = Field(None, description="Innovation actors")
    # organizations_detailed: Optional[List[OrganizationModel]] = Field(None, description="Organizations")

    organizations: Optional[List[str]] = Field(None, description="List of organization names")
    organization_type: Optional[List[str]] = Field(None, description="List of organization types")
    organization_sub_type: Optional[str] = Field(None, description="Organization subtype")
    other_organization_type: Optional[str] = Field(None, description="Other organization type if type is 'Other'")

    @field_validator('assess_readiness', mode='before')
    @classmethod
    def validate_readiness(cls, v):
        """Validate readiness level (0-9) or 'Not collected'"""
        if v is None or v == "Not collected":
            return None
        if isinstance(v, str) and v.isdigit():
            v = int(v)
        if isinstance(v, int) and 0 <= v <= 9:
            return v
        return None
    
    @field_validator('anticipated_users')
    @classmethod
    def validate_anticipated_users(cls, v):
        """Validate anticipated users values"""
        valid_values = ["This is yet to be determined", "Users have been determined"]
        if v and v not in valid_values:
            return "This is yet to be determined"
        return v
    
    @field_validator('organizations', 'organization_type', mode='before')
    @classmethod
    def ensure_lists(cls, v):
        """Ensure organization fields are lists"""
        if v is None:
            return None
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [str(item) for item in v if item]
        return []


ResultModel = Union[CapacityDevelopmentResult, PolicyChangeResult, InnovationDevelopmentResult]

class MiningResponse(BaseModel):
    """Complete mining response"""
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