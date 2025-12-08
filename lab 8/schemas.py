from pydantic import BaseModel

class PatientBase(BaseModel):
    name: str
    age: int
    is_active: bool = True
    description: str | None = None

class PatientCreate(PatientBase):
    pass

class PatientRead(PatientBase):
    id: int

    class Config:
        orm_mode = True
