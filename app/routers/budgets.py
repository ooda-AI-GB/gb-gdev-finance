from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models import Budget, Category
from app.schemas import BudgetCreate, BudgetUpdate, BudgetResponse
from app.auth import get_api_key

router = APIRouter(prefix="/budgets", tags=["Budgets"])


@router.get("/", response_model=List[BudgetResponse])
def list_budgets(
    year: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    period: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: str = Depends(get_api_key),
):
    q = db.query(Budget)
    if year:
        q = q.filter(Budget.year == year)
    if category_id:
        q = q.filter(Budget.category_id == category_id)
    if period:
        q = q.filter(Budget.period == period)
    return q.offset(skip).limit(limit).all()


@router.post("/", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    data: BudgetCreate,
    db: Session = Depends(get_db),
    _: str = Depends(get_api_key),
):
    if not db.query(Category).filter(Category.id == data.category_id).first():
        raise HTTPException(status_code=404, detail="Category not found")
    budget = Budget(**data.model_dump())
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@router.get("/{budget_id}", response_model=BudgetResponse)
def get_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_api_key),
):
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return budget


@router.put("/{budget_id}", response_model=BudgetResponse)
def update_budget(
    budget_id: int,
    data: BudgetUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(get_api_key),
):
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    update_data = data.model_dump(exclude_unset=True)
    if "category_id" in update_data:
        if not db.query(Category).filter(Category.id == update_data["category_id"]).first():
            raise HTTPException(status_code=404, detail="Category not found")
    for field, value in update_data.items():
        setattr(budget, field, value)
    db.commit()
    db.refresh(budget)
    return budget


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_api_key),
):
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    db.delete(budget)
    db.commit()
