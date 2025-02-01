from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date

class ContactCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    birthday: Optional[date]
    additional_info: Optional[str]

class ContactRead(ContactCreate):
    id: int

    class Config:
        orm_mode = True
