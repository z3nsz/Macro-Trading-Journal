from pydantic import BaseModel, ConfigDict

from app.schemas.common import LongText, Name


class StrategyCreate(BaseModel):
    name: Name
    description: LongText | None = None


class StrategyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
