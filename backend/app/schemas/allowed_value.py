"""Pydantic schemas for the AllowedValue controlled vocabulary."""

from pydantic import BaseModel


class AllowedValueResponse(BaseModel):
    Id: str
    Value_Group: str
    Code: str
    Label: str
    Display_Order: int
    Is_Active: bool
    Description: str | None

    model_config = {"from_attributes": True}
