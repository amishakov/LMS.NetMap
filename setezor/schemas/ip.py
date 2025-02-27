from pydantic import BaseModel


class IPSchema(BaseModel):
    id: int
    mac_id: int | None
    ip: str

    class Config:
        from_attributes = True


class IPSchemaAdd(BaseModel):
    mac_id: int | None
    ip: str | None


class ChangeObjectType(BaseModel):
    ip_id: str
    object_type_id: str
