from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.auth import get_api_key
from app.database import get_db
from app.models import Category, Report, Transaction
from app.schemas import ReportCreate, ReportResponse, ReportUpdate

router = APIRouter(prefix="/reports", tags=["Reports"])

# ---------------------------------------------------------------------------
# Deductibility factors per tax category
# ---------------------------------------------------------------------------
TAX_DEDUCTIBILITY: Dict[str, float] = {
    "business_expense": 1.0,
    "meals_entertainment": 0.5,
    "depreciation": 1.0,   # simplified — real depreciation is scheduled
    "medical_expense": 1.0,
    "income": 0.0,
    "not_deductible": 0.0,
    "pending_review": 0.0,
}

# ---------------------------------------------------------------------------
# On-the-fly report endpoints  (defined BEFORE /{report_id} to take priority)
# ---------------------------------------------------------------------------

@router.get("/tax-summary")
def tax_summary_report(
    year: int = Query(..., description="Tax year, e.g. 2025"),
    db: Session = Depends(get_db),
    _: str = Depends(get_api_key),
):
    """
    Summarise deductible and non-deductible expenses for a given tax year,
    grouped by tax category.
    """
    start = date(year, 1, 1)
    end = date(year, 12, 31)

    # All transactions for the year with a category
    txns = (
        db.query(Transaction)
        .filter(Transaction.date >= start, Transaction.date <= end)
        .all()
    )

    total_income: float = 0.0
    total_expenses: float = 0.0
    by_tax_cat: Dict[str, Dict[str, Any]] = {}
    pending_review_count = 0

    for txn in txns:
        amount = float(txn.amount)
        tax_cat = txn.tax_category or "pending_review"

        if tax_cat == "income":
            total_income += amount
            continue

        expense_amt = abs(amount)
        total_expenses += expense_amt
        factor = TAX_DEDUCTIBILITY.get(tax_cat, 0.0)
        deductible = round(expense_amt * factor, 2)

        if tax_cat not in by_tax_cat:
            by_tax_cat[tax_cat] = {
                "gross_amount": 0.0,
                "deductible_amount": 0.0,
                "transaction_count": 0,
                "deductibility_rate": factor,
            }
        by_tax_cat[tax_cat]["gross_amount"] = round(by_tax_cat[tax_cat]["gross_amount"] + expense_amt, 2)
        by_tax_cat[tax_cat]["deductible_amount"] = round(by_tax_cat[tax_cat]["deductible_amount"] + deductible, 2)
        by_tax_cat[tax_cat]["transaction_count"] += 1

        if tax_cat == "pending_review":
            pending_review_count += 1

    total_deductible = sum(v["deductible_amount"] for v in by_tax_cat.values())

    # Unclassified (no category at all)
    unclassified_count = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.date >= start, Transaction.date <= end, Transaction.category_id.is_(None))
        .scalar()
    ) or 0

    return {
        "year": year,
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "total_deductible": round(total_deductible, 2),
        "net_income": round(total_income - total_expenses, 2),
        "by_tax_category": by_tax_cat,
        "unclassified_count": unclassified_count,
        "transactions_pending_review": pending_review_count,
    }


@router.get("/monthly")
def monthly_report(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    _: str = Depends(get_api_key),
):
    """Income, expenses, and per-category breakdown for a single month."""
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    start = date(year, month, 1)
    end = date(year, month, last_day)

    txns = (
        db.query(Transaction)
        .filter(Transaction.date >= start, Transaction.date <= end)
        .all()
    )

    total_income = 0.0
    total_expenses = 0.0
    category_totals: Dict[str, Dict[str, Any]] = {}

    for txn in txns:
        amount = float(txn.amount)
        cat_name = txn.category_name or "Uncategorized"
        cat_type = txn.category_obj.type if txn.category_obj else "expense"

        if cat_type == "income":
            total_income += amount
        else:
            total_expenses += abs(amount)

        if cat_name not in category_totals:
            category_totals[cat_name] = {
                "category_id": txn.category_id,
                "category_name": cat_name,
                "type": cat_type,
                "amount": 0.0,
                "count": 0,
            }
        category_totals[cat_name]["amount"] = round(category_totals[cat_name]["amount"] + abs(amount), 2)
        category_totals[cat_name]["count"] += 1

    by_category = sorted(category_totals.values(), key=lambda x: x["amount"], reverse=True)

    return {
        "year": year,
        "month": month,
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "net": round(total_income - total_expenses, 2),
        "transaction_count": len(txns),
        "by_category": by_category,
    }


@router.get("/category")
def category_report(
    category_id: int = Query(..., description="Category ID to report on"),
    start: Optional[date] = Query(None, description="Start date (inclusive), e.g. 2025-01-01"),
    end: Optional[date] = Query(None, description="End date (inclusive), e.g. 2025-12-31"),
    db: Session = Depends(get_db),
    _: str = Depends(get_api_key),
):
    """Detailed breakdown of transactions for a specific category over a date range."""
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    q = db.query(Transaction).filter(Transaction.category_id == category_id)
    if start:
        q = q.filter(Transaction.date >= start)
    if end:
        q = q.filter(Transaction.date <= end)
    txns = q.order_by(Transaction.date).all()

    total_amount = sum(abs(float(t.amount)) for t in txns)
    count = len(txns)
    average = round(total_amount / count, 2) if count else 0.0

    # Monthly breakdown
    monthly: Dict[str, Dict[str, Any]] = {}
    for txn in txns:
        key = f"{txn.date.year}-{txn.date.month:02d}"
        if key not in monthly:
            monthly[key] = {"year": txn.date.year, "month": txn.date.month, "amount": 0.0, "count": 0}
        monthly[key]["amount"] = round(monthly[key]["amount"] + abs(float(txn.amount)), 2)
        monthly[key]["count"] += 1

    return {
        "category": {
            "id": cat.id,
            "name": cat.name,
            "type": cat.type,
            "tax_category": cat.tax_category,
        },
        "start_date": start.isoformat() if start else None,
        "end_date": end.isoformat() if end else None,
        "total_amount": round(total_amount, 2),
        "transaction_count": count,
        "average_transaction": average,
        "monthly_breakdown": sorted(monthly.values(), key=lambda x: (x["year"], x["month"])),
        "transactions": [
            {
                "id": t.id,
                "date": t.date.isoformat(),
                "description": t.description,
                "amount": float(t.amount),
                "vendor": t.vendor,
                "tax_deductible": t.tax_deductible,
            }
            for t in txns
        ],
    }


# ---------------------------------------------------------------------------
# Saved report CRUD
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[ReportResponse])
def list_reports(
    type: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: str = Depends(get_api_key),
):
    q = db.query(Report)
    if type:
        q = q.filter(Report.type == type)
    return q.order_by(Report.generated_at.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(
    data: ReportCreate,
    db: Session = Depends(get_db),
    _: str = Depends(get_api_key),
):
    report = Report(**data.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_api_key),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.put("/{report_id}", response_model=ReportResponse)
def update_report(
    report_id: int,
    data: ReportUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(get_api_key),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(report, field, value)
    db.commit()
    db.refresh(report)
    return report


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_api_key),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    db.delete(report)
    db.commit()
