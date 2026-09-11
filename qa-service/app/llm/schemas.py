from pydantic import BaseModel

class ImpactAreaScoresSchema(BaseModel):
    social_inclusion: str
    climate_adaptation: str
    food_security: str
    environmental_health: str
    poverty_reduction: str


class InnovationDevSchema(BaseModel):
    new_title: str
    new_description: str
    short_name: str
    impact_area_scores: ImpactAreaScoresSchema


class KnowledgeProductSchema(BaseModel):
    impact_area_scores: ImpactAreaScoresSchema


class NonInnovationDevSchema(BaseModel):
    new_title: str
    new_description: str
    impact_area_scores: ImpactAreaScoresSchema


def validate_output_schema(json_content: dict, result_type: str):
    if result_type == "innovation development":
        return InnovationDevSchema(**json_content)
    elif result_type == "knowledge product":
        return KnowledgeProductSchema(**json_content)
    else:
        return NonInnovationDevSchema(**json_content)