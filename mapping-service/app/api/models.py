from pydantic import BaseModel
from typing import Literal, List, Optional

class MappingEntry(BaseModel):
    value: str
    type: Literal["staff", "institution"]

class MappingRequest(BaseModel):
    entries: List[MappingEntry]

class MappingResult(BaseModel):
    original_value: str
    type: str
    mapped_id: Optional[str]
    mapped_name: Optional[str]
    mapped_acronym: Optional[str] = None
    score: Optional[float]

class MappingResponse(BaseModel):
    results: List[MappingResult]