from typing import Dict, Optional, TypeVar, Generic, Any
from pydantic import BaseModel

T = TypeVar('T')


class MisConfigDto(BaseModel):
    acronym: str
    environment: str


class ResMisConfigDto(MisConfigDto):
    code: int
    name: str


class ClarisaCreateConnectionDto(BaseModel):
    sender_mis: MisConfigDto
    receiver_mis: MisConfigDto


class ResClarisaValidateConnectionDto(BaseModel):
    client_id: str
    sender_mis: ResMisConfigDto
    receiver_mis: ResMisConfigDto


class ResClarisaCreateConnectionDto(ResClarisaValidateConnectionDto):
    secret: str


class ClarisaSecret(BaseModel):
    client_id: str
    secret: str


class ResponseValidateClarisa(Generic[T]):
    def __init__(self, data: Optional[T], valid: bool):
        self.data = data
        self.valid = valid


class ResponseClarisaDto(BaseModel):
    status: int
    response: Any
