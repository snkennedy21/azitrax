from pydantic import Field

from app.schemas.common import APIBaseModel


class PointListItem(APIBaseModel):
    id: int = Field(description="Unique point identifier")
    lat: float = Field(description="Latitude coordinate (WGS84)")
    lon: float = Field(description="Longitude coordinate (WGS84)")
