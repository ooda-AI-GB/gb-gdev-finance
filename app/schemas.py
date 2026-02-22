from pydantic import BaseModel, ConfigDict, field_validator
from datetime import date, datetime
from typing import Optional, List, Any, Dict


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------

class CategoryBase(BaseModel):
    name: str
    type: str
    parent_id: Optional[int] = None
    tax_category: Optional[str] = None
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    parent_id: Optional[int] = None
    tax_category: Optional[str] = None
    description: Optional[str] = None


class CategoryResponse(CategoryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------

class AccountBase(BaseModel):
    name: str
    type: str
    institution: Optional[str] = None
    last_four: Optional[str] = None
    currency: str = "USD"
    balance: float = 0.0


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    institution: Optional[str] = None
    last_four: Optional[str] = None
    currency: Optional[str] = None
    balance: Optional[float] = None


class AccountResponse(AccountBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------

class TransactionBase(BaseModel):
    date: date
    description: str
    amount: float
    currency: str = "USD"
    category_id: Optional[int] = None
    subcategory: Optional[str] = None
    vendor: Optional[str] = None
    payment_method: Optional[str] = None
    is_business: bool = True
    tax_deductible: bool = False
    notes: Optional[str] = None
    receipt_url: Optional[str] = None


class TransactionCreate(TransactionBase):
    source: str = "manual"


class TransactionUpdate(BaseModel):
    date: Optional[date] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    category_id: Optional[int] = None
    subcategory: Optional[str] = None
    vendor: Optional[str] = None
    payment_method: Optional[str] = None
    is_business: Optional[bool] = None
    tax_deductible: Optional[bool] = None
    notes: Optional[str] = None
    receipt_url: Optional[str] = None
    source: Optional[str] = None


class TransactionResponse(TransactionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source: str
    category_name: Optional[str] = None
    tax_category: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ClassifyRequest(BaseModel):
    description: str
    vendor: Optional[str] = None


class ClassifyResponse(BaseModel):
    category_id: Optional[int]
    category_name: Optional[str]
    tax_category: Optional[str]
    confidence: float
    match_count: int


class ImportResult(BaseModel):
    imported: int
    failed: int
    errors: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------

class BudgetBase(BaseModel):
    category_id: int
    period: str
    amount: float
    year: int
    month: Optional[int] = None


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    category_id: Optional[int] = None
    period: Optional[str] = None
    amount: Optional[float] = None
    year: Optional[int] = None
    month: Optional[int] = None


class BudgetResponse(BudgetBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    category_name: Optional[str] = None


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

class ReportBase(BaseModel):
    name: str
    type: str
    parameters: Optional[Dict[str, Any]] = None


class ReportCreate(ReportBase):
    pass


class ReportUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class ReportResponse(ReportBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    generated_at: datetime
