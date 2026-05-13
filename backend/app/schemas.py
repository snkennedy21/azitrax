from pydantic import BaseModel, ConfigDict, Field


def to_camel(string: str) -> str:
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class APIBaseModel(BaseModel):
    """Base model with camelCase alias generation for API responses.

    This base class configures Pydantic to:
    - Accept both snake_case (Python) and camelCase (API) field names in input
    - Serialize fields as camelCase in API responses
    - Allow internal Python code to use snake_case naming
    """

    model_config = ConfigDict(
        # Allow validation from both snake_case (internal) and camelCase (API)
        populate_by_name=True,
        # Generate camelCase aliases for all fields
        alias_generator=to_camel,
    )


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


class AisVesselRecord(APIBaseModel):
    mmsi: int = Field(description="Maritime Mobile Service Identity")
    ship_name: str | None = Field(default=None, description="Vessel name when provided by AIS source")
    lat: float = Field(ge=-90, le=90, description="Latitude coordinate (WGS84)")
    lon: float = Field(ge=-180, le=180, description="Longitude coordinate (WGS84)")
    time_utc: str | None = Field(default=None, description="Source receive time in UTC when provided")
    sog: float | None = Field(default=None, description="Speed over ground")
    cog: float | None = Field(default=None, description="Course over ground")
    true_heading: int | None = Field(default=None, description="True heading")
    navigational_status: int | None = Field(default=None, description="AIS navigational status")
    position_accuracy: bool | None = Field(default=None, description="AIS position accuracy flag")
