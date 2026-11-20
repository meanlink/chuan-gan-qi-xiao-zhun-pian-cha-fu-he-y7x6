from pydantic import BaseModel, Field
class CaseInput(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    job_id: int
    tolerances: dict[str, float] = Field(min_length=1, max_length=50)
class EnableInput(BaseModel):
    holdback_id: int
