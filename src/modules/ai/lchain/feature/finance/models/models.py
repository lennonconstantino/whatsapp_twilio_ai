"""
Modelos Pydantic para integração com Supabase
Substitui SQLModel mantendo validações e lógica de negócio
"""
from typing import Optional
from pydantic import BaseModel, BeforeValidator, model_validator, Field
from datetime import time, datetime
from typing_extensions import Annotated


# === Validators ===
def validate_date(v):
    """Valida e converte diferentes formatos de data para datetime"""
    if isinstance(v, datetime):
        return v

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


def validate_time(v):
    """Valida e converte string para time"""
    if isinstance(v, time):
        return v

    if isinstance(v, str):
        try:
            return time.fromisoformat(v)
        except ValueError:
            raise ValueError("Invalid time format")
    
    raise ValueError("Value must be a time object or ISO format string")


def numeric_validator(v):
    """Garante que valores numéricos sejam float"""
    if isinstance(v, int):
        return float(v)
    elif isinstance(v, float):
        return v
    raise ValueError("Value must be a number")


# Tipos customizados
DateFormat = Annotated[datetime, BeforeValidator(validate_date)]
TimeFormat = Annotated[time, BeforeValidator(validate_time)]
Numeric = Annotated[float, BeforeValidator(numeric_validator)]


# ==== Base Models ====

class RevenueBase(BaseModel):
    """Modelo base para Revenue (sem ID)"""
    description: str
    net_amount: Numeric
    gross_amount: Numeric
    tax_rate: Numeric
    date: DateFormat

    @model_validator(mode="before")
    @classmethod
    def check_net_gross(cls, data: any):
        """Calcula automaticamente valores faltantes entre net, gross e tax_rate"""
        if isinstance(data, dict):
            if "net_amount" in data and "tax_rate" in data:
                data["gross_amount"] = round(data["net_amount"] * (1 + data["tax_rate"]), 2)
            elif "gross_amount" in data and "tax_rate" in data:
                data["net_amount"] = round(data["gross_amount"] / (1 + data["tax_rate"]), 2)
            elif "net_amount" in data and "gross_amount" in data:
                data["tax_rate"] = round((data["gross_amount"] - data["net_amount"]) / data["net_amount"], 2)

        return data


class RevenueCreate(RevenueBase):
    """Schema para criação de Revenue (INSERT)"""
    pass


class RevenueUpdate(BaseModel):
    """Schema para atualização de Revenue (UPDATE)"""
    description: Optional[str] = None
    net_amount: Optional[Numeric] = None
    gross_amount: Optional[Numeric] = None
    tax_rate: Optional[Numeric] = None
    date: Optional[DateFormat] = None


class Revenue(RevenueBase):
    """Schema completo de Revenue (SELECT) - inclui ID"""
    id: int
    
    class Config:
        from_attributes = True


# ==== Expense Models ====

class ExpenseBase(BaseModel):
    """Modelo base para Expense (sem ID)"""
    description: str
    net_amount: Numeric = Field(description="The net amount of the expense (before tax)")
    gross_amount: Numeric
    tax_rate: Numeric
    date: DateFormat

    @model_validator(mode="before")
    @classmethod
    def check_net_gross(cls, data: any):
        """Calcula automaticamente valores faltantes entre net, gross e tax_rate"""
        if isinstance(data, dict):
            if "net_amount" in data and "tax_rate" in data:
                data["gross_amount"] = round(data["net_amount"] * (1 + data["tax_rate"]), 2)
            elif "gross_amount" in data and "tax_rate" in data:
                data["net_amount"] = round(data["gross_amount"] / (1 + data["tax_rate"]), 2)
            elif "net_amount" in data and "gross_amount" in data:
                data["tax_rate"] = round((data["gross_amount"] - data["net_amount"]) / data["net_amount"], 2)

        return data


class ExpenseCreate(ExpenseBase):
    """Schema para criação de Expense (INSERT)"""
    pass


class ExpenseUpdate(BaseModel):
    """Schema para atualização de Expense (UPDATE)"""
    description: Optional[str] = None
    net_amount: Optional[Numeric] = None
    gross_amount: Optional[Numeric] = None
    tax_rate: Optional[Numeric] = None
    date: Optional[DateFormat] = None


class Expense(ExpenseBase):
    """Schema completo de Expense (SELECT) - inclui ID"""
    id: int
    
    class Config:
        from_attributes = True


# ==== Customer Models ====

class CustomerBase(BaseModel):
    """Modelo base para Customer (sem ID)"""
    company_name: Optional[str] = None
    first_name: str
    last_name: str
    phone: str
    address: str
    city: str
    zip: str
    country: str


class CustomerCreate(CustomerBase):
    """Schema para criação de Customer (INSERT)"""
    pass


class CustomerUpdate(BaseModel):
    """Schema para atualização de Customer (UPDATE)"""
    company_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    zip: Optional[str] = None
    country: Optional[str] = None


class Customer(CustomerBase):
    """Schema completo de Customer (SELECT) - inclui ID"""
    id: int
    
    class Config:
        from_attributes = True


# ==== Invoice Models ====

class InvoiceBase(BaseModel):
    """Modelo base para Invoice (sem ID)"""
    customer_id: Optional[int] = None
    invoice_number: str
    description: str
    amount: Numeric
    tax_rate: Numeric
    date: DateFormat


class InvoiceCreate(InvoiceBase):
    """Schema para criação de Invoice (INSERT)"""
    pass


class InvoiceUpdate(BaseModel):
    """Schema para atualização de Invoice (UPDATE)"""
    customer_id: Optional[int] = None
    invoice_number: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[Numeric] = None
    tax_rate: Optional[Numeric] = None
    date: Optional[DateFormat] = None


class Invoice(InvoiceBase):
    """Schema completo de Invoice (SELECT) - inclui ID"""
    id: int
    
    class Config:
        from_attributes = True
