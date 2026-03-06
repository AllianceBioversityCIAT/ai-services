import re
from datetime import datetime
from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


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
        if v is None:
            return None
        if isinstance(v, str) and v.isdigit():
            v = int(v)
        if isinstance(v, int) and v >= 0:
            return v
        return None
    
    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_dates(cls, v):
        """Validate date format (YYYY-MM-DD)"""
        if v is None:
            return None
        if isinstance(v, str) and re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            return v
        return None
    
    @field_validator('length_of_training')
    @classmethod
    def validate_training_length(cls, v):
        """Validate training length values"""
        if v and v not in ["Short-term", "Long-term"]:
            return None
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
        valid_types = ["Policy or Strategy", "Legal instrument", "Program, Budget, or Investment"]
        if v and v not in valid_types:
            return None
        return v
    
    @field_validator('stage_in_policy_process')
    @classmethod
    def validate_policy_stage(cls, v):
        """Validate policy stage values"""
        valid_stages = [
            "Stage 1: Research taken up by next user, policy change not yet enacted.",
            "Stage 2: Policy enacted.",
            "Stage 3: Evidence of impact of policy."
        ]
        if v and v not in valid_stages:
            return None
        return v


class InnovationActorModel(BaseModel):
    """Individual actor involved in innovation"""
    model_config = ConfigDict(exclude_none=True)
    
    name: Optional[str] = Field(None, description="Actor name (optional - can be partial entry)")
    type: str = Field(..., description="Actor type")
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


# class OrganizationModel(BaseModel):
#     """Organization involved in innovation"""
    # name: str = Field(..., description="Organization name")
    # type: str = Field(..., description="Organization type(s)")
    # sub_type: Optional[str] = Field(None, description="Organization subtype")
    # other_type: Optional[str] = Field(None, description="Other organization type if type is 'Other'")


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

    # organizations: Optional[List[str]] = Field(None, description="List of organization names")
    # organization_type: Optional[List[str]] = Field(None, description="List of organization types")
    # organization_sub_type: Optional[str] = Field(None, description="Organization subtype")
    # other_organization_type: Optional[str] = Field(None, description="Other organization type if type is 'Other'")

    @field_validator('innovation_nature')
    @classmethod
    def validate_innovation_nature(cls, v):
        """Validate innovation nature values"""
        valid_natures = [
            "Incremental innovation",
            "Radical innovation",
            "Disruptive innovation",
            "Other"
        ]
        if v and v not in valid_natures:
            return "Other"
        return v
    
    @field_validator('innovation_type')
    @classmethod
    def validate_innovation_type(cls, v):
        """Validate innovation type values"""
        valid_types = [
            "Technological innovation",
            "Capacity development innovation",
            "Policy, organizational or institutional innovation",
            "Other"
        ]
        if v and v not in valid_types:
            return "Other"
        return v

    @field_validator('assess_readiness', mode='before')
    @classmethod
    def validate_readiness(cls, v):
        """Validate readiness level (0-9)"""
        if v is None:
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
    
    # @field_validator('organizations', 'organization_type', mode='before')
    # @classmethod
    # def ensure_lists(cls, v):
    #     """Ensure organization fields are lists"""
    #     if v is None:
    #         return None
    #     if isinstance(v, str):
    #         return [v]
    #     if isinstance(v, list):
    #         return [str(item) for item in v if item]
    #     return []
    
    # @model_validator(mode='after')
    # def validate_organization_sub_type(self):
    #     """Validate organization_sub_type and other_organization_type based on organization_type"""
    #     org_types = self.organization_type
    #     org_sub_type = self.organization_sub_type
    #     other_org_type = self.other_organization_type
        
    #     # Validate other_organization_type - only allowed if "Other" is in organization_type
    #     if other_org_type:
    #         if not org_types or "Other" not in org_types:
    #             self.other_organization_type = None
        
    #     # If no organization_sub_type provided, that's fine (it's optional)
    #     if not org_sub_type:
    #         return self
        
    #     # If no organization_type, but org_sub_type exists, remove org_sub_type
    #     if not org_types or len(org_types) == 0:
    #         self.organization_sub_type = None
    #         return self
        
    #     # Define valid subtypes for each organization type
    #     valid_subtypes_map = {
    #         "NGO": [
    #             "NGO International", "NGO International (General)", "NGO International (Farmers)",
    #             "NGO Regional", "NGO Regional (General)", "NGO Regional (Farmers)",
    #             "NGO National", "NGO National (General)", "NGO National (Farmers)",
    #             "NGO Local", "NGO Local (General)", "NGO Local (Farmers)"
    #         ],
    #         "Research organizations and universities": [
    #             "Research organizations and universities International",
    #             "Research organizations and universities International (General)",
    #             "Research organizations and universities International (Universities)",
    #             "Research organizations and universities International (CGIAR)",
    #             "Research organizations and universities Regional",
    #             "Research organizations and universities Regional (NA)",
    #             "Research organizations and universities Regional (Universities)",
    #             "Research organizations and universities National",
    #             "Research organizations and universities National (NARS)",
    #             "Research organizations and universities National (Universities)",
    #             "Research organizations and universities Local",
    #             "Research organizations and universities Local (NA)",
    #             "Research organizations and universities Local (Universities)"
    #         ],
    #         "Organization (other than financial or research)": [
    #             "Organization (other than financial or research) International",
    #             "Organization (other than financial or research) Regional"
    #         ],
    #         "Government": [
    #             "Government (National)",
    #             "Government (Subnational)"
    #         ],
    #         "Financial institution": [
    #             "Financial Institution",
    #             "Financial Institution International",
    #             "Financial Institution Regional",
    #             "Financial Institution National",
    #             "Financial Institution Local"
    #         ]
    #     }
        
    #     # Types that don't use organization_sub_type
    #     no_subtype_types = [
    #         "Private company (other than financial)",
    #         "Public-Private Partnership",
    #         "Foundation",
    #         "Other"
    #     ]
        
    #     # Check if any org_type is in the no_subtype list
    #     if any(ot in no_subtype_types for ot in org_types):
    #         # If all types are no-subtype types, remove org_sub_type
    #         if all(ot in no_subtype_types for ot in org_types):
    #             self.organization_sub_type = None
    #             return self
        
    #     # Validate that org_sub_type matches at least one org_type
    #     is_valid = False
    #     for org_type in org_types:
    #         if org_type in valid_subtypes_map:
    #             if org_sub_type in valid_subtypes_map[org_type]:
    #                 is_valid = True
    #                 break
        
    #     # If invalid, set to None (will be excluded from JSON)
    #     if not is_valid:
    #         self.organization_sub_type = None
        
    #     return self


ResultModel = Union[CapacityDevelopmentResult, PolicyChangeResult, InnovationDevelopmentResult]


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