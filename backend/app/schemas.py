from typing import Any
from typing import Literal

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


class LiveVesselMapItem(APIBaseModel):
    """Temporary live map render contract, not a persisted vessel domain model."""

    id: str = Field(description="Stable frontend marker identifier derived from the live source")
    lat: float = Field(ge=-90, le=90, description="Latitude coordinate (WGS84)")
    lon: float = Field(ge=-180, le=180, description="Longitude coordinate (WGS84)")
    timestamp: str | None = Field(default=None, description="Source timestamp for this live position")
    last_seen_at: str | None = Field(
        default=None,
        description="UTC time this vessel snapshot was last refreshed",
    )
    freshness: Literal["fresh", "stale"] | None = Field(
        default=None,
        description="Freshness state derived from lastSeenAt",
    )
    mmsi: int | None = Field(default=None, description="Maritime Mobile Service Identity when available")
    label: str | None = Field(default=None, description="Display label for the vessel marker")
    course: float | None = Field(default=None, description="Course over ground")
    heading: int | None = Field(default=None, description="True heading")
    speed: float | None = Field(default=None, description="Speed over ground")
    destination: str | None = Field(default=None, description="Reported destination when available")


class CachedLiveVessel(APIBaseModel):
    """Live Redis vessel snapshot contract, not durable vessel persistence."""

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        allow_inf_nan=False,
    )

    id: str = Field(description="Stable frontend marker identifier derived from the live source")
    mmsi: int = Field(description="Maritime Mobile Service Identity")
    lat: float = Field(ge=-90, le=90, description="Latitude coordinate (WGS84)")
    lon: float = Field(ge=-180, le=180, description="Longitude coordinate (WGS84)")
    timestamp: str | None = Field(default=None, description="Source timestamp for this live position")
    label: str | None = Field(default=None, description="Display label for the vessel marker")
    course: float | None = Field(default=None, description="Course over ground")
    heading: int | None = Field(default=None, description="True heading")
    speed: float | None = Field(default=None, description="Speed over ground")
    destination: str | None = Field(default=None, description="Reported destination when available")
    first_seen_at: str = Field(description="UTC time this vessel first entered the live Redis snapshot")
    last_seen_at: str = Field(description="UTC time this vessel snapshot was last refreshed")
    last_message_at: str = Field(description="UTC source message time used for freshness checks")


class LiveVesselsMetadata(APIBaseModel):
    source: str = Field(description="Configured AIS source for the live snapshot")
    fetched_at: str = Field(description="API snapshot read completion time in UTC")
    known_count: int = Field(description="Number of vessel IDs known in the live Redis snapshot")
    returned_count: int = Field(description="Number of live vessel items returned")
    last_message_at: str | None = Field(default=None, description="Newest source message time in returned items")
    oldest_last_seen_at: str | None = Field(default=None, description="Oldest cache refresh time in returned items")
    source_status: dict[str, Any] = Field(description="Latest live source status reported by the consumer")
    bounding_boxes: list[Any] = Field(description="AIS source bounding boxes configured for the live snapshot")


class LiveVesselsResponse(APIBaseModel):
    items: list[LiveVesselMapItem] = Field(description="Minimal live vessel items for map rendering")
    metadata: LiveVesselsMetadata = Field(description="Fetch metadata for poll freshness checks")
