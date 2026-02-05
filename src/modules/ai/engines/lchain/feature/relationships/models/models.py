"""
Modelos Pydantic para o módulo de Relacionamentos
Seguindo o padrão do módulo Finance
"""

from datetime import datetime, date, time
from typing import Optional, List

from pydantic import BaseModel, BeforeValidator, Field, model_validator
from typing_extensions import Annotated


# === Validators ===
def validate_date(v):
    """Valida e converte diferentes formatos de data para datetime"""
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day)

    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v)
        except ValueError:
            pass

        for f in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"]:
            try:
                return datetime.strptime(v, f)
            except ValueError:
                pass

    raise ValueError("Invalid date format")


def validate_date_only(v):
    """Valida e converte para date object"""
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v).date()
        except ValueError:
            pass
        try:
            return datetime.strptime(v, "%Y-%m-%d").date()
        except ValueError:
            pass
            
    raise ValueError("Invalid date format")
    
# Tipos customizados
DateFormat = Annotated[datetime, BeforeValidator(validate_date)]
DateOnlyFormat = Annotated[date, BeforeValidator(validate_date_only)]


# ==== Person Models ====

class PersonBase(BaseModel):
    """Modelo base para Person"""
    first_name: str
    last_name: str
    phone: str
    tags: Optional[str] = None
    birthday: Optional[DateOnlyFormat] = None
    city: Optional[str] = None
    notes: Optional[str] = None


class PersonCreate(PersonBase):
    """Schema para criação de Person (INSERT)"""
    pass


class PersonUpdate(BaseModel):
    """Schema para atualização de Person (UPDATE)"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    tags: Optional[str] = None
    birthday: Optional[DateOnlyFormat] = None
    city: Optional[str] = None
    notes: Optional[str] = None


class Person(PersonBase):
    """Schema completo de Person (SELECT) - inclui ID"""
    id: int

    class Config:
        from_attributes = True


# ==== Interaction Models ====

class InteractionBase(BaseModel):
    """Modelo base para Interaction"""
    person_id: int
    date: DateFormat
    channel: str
    type: str
    summary: Optional[str] = None
    sentiment: Optional[float] = None


class InteractionCreate(InteractionBase):
    """Schema para criação de Interaction"""
    pass


class InteractionUpdate(BaseModel):
    """Schema para atualização de Interaction"""
    person_id: Optional[int] = None
    date: Optional[DateFormat] = None
    channel: Optional[str] = None
    type: Optional[str] = None
    summary: Optional[str] = None
    sentiment: Optional[float] = None


class Interaction(InteractionBase):
    """Schema completo de Interaction"""
    id: int

    class Config:
        from_attributes = True


# ==== Reminder Models ====

class ReminderBase(BaseModel):
    """Modelo base para Reminder"""
    person_id: int
    due_date: DateFormat
    reason: str
    status: str = Field(default="open")


class ReminderCreate(ReminderBase):
    """Schema para criação de Reminder"""
    pass


class ReminderUpdate(BaseModel):
    """Schema para atualização de Reminder"""
    person_id: Optional[int] = None
    due_date: Optional[DateFormat] = None
    reason: Optional[str] = None
    status: Optional[str] = None


class Reminder(ReminderBase):
    """Schema completo de Reminder"""
    id: int

    class Config:
        from_attributes = True
