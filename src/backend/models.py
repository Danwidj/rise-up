from typing import Literal, Optional
from pydantic import BaseModel, Field

# -------------------------
# Shared Image Model
# -------------------------

class ImageReference(BaseModel):
    uri: str = Field(..., description="Path or URL to the cropped image")
    frame_number: Optional[int] = Field(
        None,
        description="Frame number the crop came from"
    )


# -------------------------
# Incident
# -------------------------

class Incident(BaseModel):
    incident_id: str = Field(..., description="Usually the video filename without extension")
    incident_type: str = Field(..., description="Category of incident")


# -------------------------
# Entity
# -------------------------

class Entity(BaseModel):
    incident_id: str
    entity_id: str = Field(..., pattern=r"^E\d+$")

    entity_type: Literal[
        "human",
        "dog",
        "cat",
        "monkey",
        "bird",
        "other"
    ]

    description: Optional[str] = None
    image: Optional[ImageReference] = None



# -------------------------
# Instrument
# -------------------------

class Instrument(BaseModel):
    incident_id: str
    instrument_id: str = Field(..., pattern=r"^I\d+$")

    instrument_type: str

    held_by_entity_id: str = Field(
        ...,
        pattern=r"^E\d+$",
        description="Entity currently holding this instrument"
    )

    description: Optional[str] = None
    image: Optional[ImageReference] = None


# -------------------------
# Asset
# -------------------------

class Asset(BaseModel):
    incident_id: str
    asset_id: str = Field(..., pattern=r"^A\d+$")

    asset_type: str

    description: Optional[str] = None
    image: Optional[ImageReference] = None
