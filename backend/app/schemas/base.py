from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base for every API schema — wire format is camelCase (per architecture
    doc §8), Python attribute names stay snake_case. populate_by_name=True
    means internal code can keep constructing these with snake_case kwargs;
    only the JSON in/out changes."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
