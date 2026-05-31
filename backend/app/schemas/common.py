from pydantic import BaseModel
from pydantic import ConfigDict


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
