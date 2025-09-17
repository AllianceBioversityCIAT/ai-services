from fastapi import APIRouter
from app.api.models import MappingRequest, MappingResponse
from app.mapping.opensearch_mapping import map_entries_to_ids

router = APIRouter()

@router.post("/fields", response_model=MappingResponse)
async def map_fields(request: MappingRequest):
    results = map_entries_to_ids(request.entries)
    return {"results": results}