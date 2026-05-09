"""API schema definitions using Pydantic models.

All API request and response models inherit from CamelCaseModel to ensure
consistent camelCase naming in API contracts while maintaining snake_case
internally in Python code.
"""

from pydantic import BaseModel, ConfigDict, Field


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase.

    Examples:
        >>> to_camel("lat")
        'lat'
        >>> to_camel("lon")
        'lon'
        >>> to_camel("created_at")
        'createdAt'
        >>> to_camel("point_count")
        'pointCount'
    """
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class CamelCaseModel(BaseModel):
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


class PointCreate(CamelCaseModel):
    """Request payload for creating a new geographic point."""

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


class PointResponse(CamelCaseModel):
    """Response model for a single point with full details.

    Returned by POST /points after creating a new point.
    """

    id: int = Field(description="Unique point identifier")
    lat: float = Field(description="Latitude coordinate (WGS84)")
    lon: float = Field(description="Longitude coordinate (WGS84)")
    srid: int = Field(description="Spatial Reference System Identifier (typically 4326 for WGS84)")


class PointListItem(CamelCaseModel):
    """Response model for a point in list views.

    Returned by GET /points. Contains minimal fields for efficient list display.
    """

    id: int = Field(description="Unique point identifier")
    lat: float = Field(description="Latitude coordinate (WGS84)")
    lon: float = Field(description="Longitude coordinate (WGS84)")
