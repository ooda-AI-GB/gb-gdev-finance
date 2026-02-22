from datetime import date, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_api_key
from app.database import get_db
from app.models import Category, Transaction

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/")
def get_dashboard(
    db: Session = Depends(get_db),
    _: str = Depends(get_api_key),
):
    """
    High-level financial overview:
    - Total income and expenses (all time)
    - Unclassified transaction count
    - Top 5 expense categories by spend
    - Monthly income/expense trend (last 12 months)
    - 5 most recent transactions
    """
    # --- All-time totals ---
    all_txns = db.query(Transaction).all()

    total_income = 0.0
    total_expenses = 0.0
    for txn in all_txns:
        amount = float(txn.amount)
        cat_type = txn.category_obj.type if txn.category_obj else "expense"
        if cat_type == "income":
            total_income += amount
        else:
            total_expenses += abs(amount)

    # --- Unclassified count ---
    unclassified_count = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.category_id.is_(None))
        .scalar()
    ) or 0

    # --- Top 5 expense categories ---
    expense_cats = (
        db.query(Category.id, Category.name, Category.tax_category)
        .filter(Category.type == "expense")
        .all()
    )
    expense_cat_ids = {c.id for c in expense_cats}
    cat_id_to_name = {c.id: c.name for c in expense_cats}
    cat_id_to_tax = {c.id: c.tax_category for c in expense_cats}

    cat_totals: Dict[int, float] = {}
    for txn in all_txns:
        if txn.category_id and txn.category_id in expense_cat_ids:
            cat_totals[txn.category_id] = cat_totals.get(txn.category_id, 0.0) + abs(float(txn.amount))

    top_categories: List[Dict[str, Any]] = []
    for cat_id, amt in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)[:5]:
        pct = round((amt / total_expenses * 100), 1) if total_expenses else 0.0
        top_categories.append({
            "category_id": cat_id,
            "category_name": cat_id_to_name[cat_id],
            "tax_category": cat_id_to_tax[cat_id],
            "amount": round(amt, 2),
            "percentage": pct,
        })

    # --- Monthly trend (last 12 months) ---
    today = date.today()
    # Start from the 1st of the month 11 months ago
    if today.month > 11:
        trend_start = date(today.year - 1, today.month - 11, 1)
    else:
        trend_start = date(today.year - 1, today.month + 1, 1)

    monthly: Dict[str, Dict[str, Any]] = {}
    for txn in all_txns:
        if txn.date < trend_start:
            continue
        key = f"{txn.date.year}-{txn.date.month:02d}"
        if key not in monthly:
            monthly[key] = {"year": txn.date.year, "month": txn.date.month, "income": 0.0, "expenses": 0.0}
        amount = float(txn.amount)
        cat_type = txn.category_obj.type if txn.category_obj else "expense"
        if cat_type == "income":
            monthly[key]["income"] = round(monthly[key]["income"] + amount, 2)
        else:
            monthly[key]["expenses"] = round(monthly[key]["expenses"] + abs(amount), 2)

    monthly_trend = sorted(monthly.values(), key=lambda x: (x["year"], x["month"]))
    for row in monthly_trend:
        row["net"] = round(row["income"] - row["expenses"], 2)

    # --- 5 most recent transactions ---
    recent = (
        db.query(Transaction)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .limit(5)
        .all()
    )
    recent_txns = [
        {
            "id": t.id,
            "date": t.date.isoformat(),
            "description": t.description,
            "amount": float(t.amount),
            "currency": t.currency,
            "category_name": t.category_name,
            "vendor": t.vendor,
        }
        for t in recent
    ]

    return {
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "net_income": round(total_income - total_expenses, 2),
        "unclassified_count": unclassified_count,
        "top_categories": top_categories,
        "monthly_trend": monthly_trend,
        "recent_transactions": recent_txns,
    }
