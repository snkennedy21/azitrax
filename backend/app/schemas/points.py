from pydantic import Field

from app.schemas.common import APIBaseModel


class PointCreate(APIBaseModel):
    lat: float = Field(
        ge=-90,
        le=90,
        description="Latitude coordinate in WGS84 spatial reference system",
    )
    lon: float = Field(
        ge=-180,
        le=180,
        description="Longitude coordinate in WGS84 spatial reference system",
    )


class PointResponse(APIBaseModel):
    id: int = Field(description="Unique point identifier")
    lat: float = Field(description="Latitude coordinate (WGS84)")
    lon: float = Field(description="Longitude coordinate (WGS84)")
    srid: int = Field(description="Spatial Reference System Identifier (typically 4326 for WGS84)")


class PointListItem(APIBaseModel):
    id: int = Field(description="Unique point identifier")
    lat: float = Field(description="Latitude coordinate (WGS84)")
    lon: float = Field(description="Longitude coordinate (WGS84)")
