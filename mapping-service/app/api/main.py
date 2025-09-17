from fastapi import FastAPI
from app.api.routes import router as mapping_router

app = FastAPI(
    title="CapDev Mapping Service",
    description="Service to map names to IDs using OpenSearch",
    version="1.0.0"
)

app.include_router(mapping_router, prefix="/map", tags=["Mapping"])