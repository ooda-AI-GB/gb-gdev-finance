import csv
import io
import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import get_api_key
from app.database import get_db
from app.models import Category, Transaction
from app.schemas import (
    ClassifyRequest,
    ClassifyResponse,
    ImportResult,
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)

router = APIRouter(prefix="/transactions", tags=["Transactions"])

# ---------------------------------------------------------------------------
# Keyword map used by the classify endpoint
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "Software & SaaS": [
        "subscription", "saas", "software", "license", "plugin", "slack", "zoom",
        "notion", "github", "gitlab", "figma", "linear", "jira", "confluence",
        "adobe", "microsoft", "google workspace", "dropbox", "hubspot", "salesforce",
        "intercom", "zendesk", "asana", "trello", "monday", "airtable", "clickup",
        "loom", "miro", "1password", "lastpass", "okta", "stripe atlas",
    ],
    "Cloud Infrastructure": [
        "aws", "amazon web services", "gcp", "google cloud", "azure", "digitalocean",
        "heroku", "vercel", "netlify", "cloudflare", "linode", "vultr", "hetzner",
        "ovh", "ec2", "s3", "rds", "lambda", "kubernetes", "k8s", "docker", "cdn",
        "hosting", "server",
    ],
    "Professional Services": [
        "consulting", "consultant", "lawyer", "attorney", "legal", "law firm",
        "accountant", "cpa", "bookkeeping", "contractor", "freelance", "agency",
        "professional service", "advisory", "staffing", "retainer",
    ],
    "Travel & Transportation": [
        "flight", "airline", "united airlines", "delta", "american airlines",
        "southwest", "jetblue", "hotel", "marriott", "hilton", "hyatt", "airbnb",
        "vrbo", "uber", "lyft", "taxi", "train", "amtrak", "rental car", "enterprise",
        "hertz", "avis", "parking", "toll", "transit", "transportation", "travel",
    ],
    "Meals & Entertainment": [
        "restaurant", "dining", "lunch", "dinner", "breakfast", "coffee", "starbucks",
        "cafe", "cafeteria", "food", "bar", "pub", "grubhub", "doordash", "ubereats",
        "seamless", "entertainment", "event", "concert", "theater", "sports",
        "team lunch", "client dinner", "client lunch",
    ],
    "Office Supplies": [
        "staples", "office depot", "officemax", "supplies", "stationery", "printer",
        "paper", "pen", "markers", "notebook", "binder", "desk", "chair", "office",
        "whiteboard", "post-it",
    ],
    "Marketing & Advertising": [
        "google ads", "adwords", "facebook ads", "meta ads", "linkedin ads",
        "twitter ads", "advertising", "marketing", "seo", "sem", "social media",
        "campaign", "promotion", "mailchimp", "constant contact", "buffer",
        "hootsuite", "canva", "brand", "public relations", "pr agency",
    ],
    "Insurance": [
        "insurance", "liability", "coverage", "policy", "premium", "workers comp",
        "health insurance", "life insurance", "disability", "business insurance",
        "general liability", "e&o", "errors and omissions",
    ],
    "Rent & Utilities": [
        "rent", "lease", "office space", "coworking", "wework", "regus",
        "electricity", "electric", "water", "gas", "natural gas", "internet",
        "broadband", "phone", "telephone", "utility", "utilities",
    ],
    "Education & Training": [
        "course", "training", "workshop", "conference", "seminar", "book",
        "textbook", "udemy", "coursera", "linkedin learning", "pluralsight",
        "skillshare", "masterclass", "certification", "tuition", "bootcamp",
        "webinar", "education", "learning",
    ],
    "Hardware & Equipment": [
        "laptop", "computer", "macbook", "iphone", "ipad", "monitor", "keyboard",
        "mouse", "headset", "camera", "server hardware", "hard drive", "ssd", "ram",
        "cpu", "gpu", "tablet", "equipment", "hardware", "device", "peripherals",
        "apple store", "best buy", "newegg", "dell", "hp", "lenovo",
    ],
    "Health & Medical": [
        "doctor", "dentist", "medical", "health", "pharmacy", "prescription",
        "hospital", "clinic", "cvs", "walgreens", "rite aid", "vision",
        "optometrist", "chiropractor", "therapy", "counseling", "gym", "fitness",
    ],
}


def _classify_text(text: str) -> tuple[int, str]:
    """Return (match_count, best_category_name) for a lowercased search string."""
    best_name = ""
    best_count = 0
    for cat_name, keywords in CATEGORY_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text)
        if count > best_count:
            best_count = count
            best_name = cat_name
    return best_count, best_name


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return bool(value)


def _parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    raise ValueError(f"Cannot parse date: {value!r}")


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[TransactionResponse])
def list_transactions(
    category_id: Optional[int] = Query(None),
    is_business: Optional[bool] = Query(None),
    tax_deductible: Optional[bool] = Query(None),
    source: Optional[str] = Query(None),
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: str = Depends(get_api_key),
):
    q = db.query(Transaction)
    if category_id is not None:
        q = q.filter(Transaction.category_id == category_id)
    if is_business is not None:
        q = q.filter(Transaction.is_business == is_business)
    if tax_deductible is not None:
        q = q.filter(Transaction.tax_deductible == tax_deductible)
    if source:
        q = q.filter(Transaction.source == source)
    if start:
        q = q.filter(Transaction.date >= start)
    if end:
        q = q.filter(Transaction.date <= end)
    return q.order_by(Transaction.date.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    data: TransactionCreate,
    db: Session = Depends(get_db),
    _: str = Depends(get_api_key),
):
    if data.category_id and not db.query(Category).filter(Category.id == data.category_id).first():
        raise HTTPException(status_code=404, detail="Category not found")
    txn = Transaction(**data.model_dump())
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_api_key),
):
    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn


@router.put("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    data: TransactionUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(get_api_key),
):
    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    update_data = data.model_dump(exclude_unset=True)
    if "category_id" in update_data and update_data["category_id"] is not None:
        if not db.query(Category).filter(Category.id == update_data["category_id"]).first():
            raise HTTPException(status_code=404, detail="Category not found")
    for field, value in update_data.items():
        setattr(txn, field, value)
    txn.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(txn)
    return txn


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_api_key),
):
    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(txn)
    db.commit()


# ---------------------------------------------------------------------------
# Import endpoint  — accepts a CSV or JSON file upload
# ---------------------------------------------------------------------------

@router.post("/import", response_model=ImportResult)
async def import_transactions(
    file: UploadFile = File(..., description="CSV or JSON file containing transactions"),
    db: Session = Depends(get_db),
    _: str = Depends(get_api_key),
):
    """
    Import transactions from a CSV or JSON file.

    **CSV columns (header required):** date, description, amount, currency,
    category_id, subcategory, vendor, payment_method, is_business, tax_deductible,
    notes, receipt_url

    **JSON format:** array of transaction objects with the same fields.
    """
    content = await file.read()
    filename = (file.filename or "").lower()

    # Detect format
    is_json = filename.endswith(".json") or (file.content_type or "").startswith("application/json")
    if not is_json:
        # Try parsing as JSON first; fall back to CSV
        try:
            rows = json.loads(content)
            is_json = True
        except (json.JSONDecodeError, UnicodeDecodeError):
            is_json = False

    if is_json:
        try:
            rows = json.loads(content) if not isinstance(content, list) else content
            if not isinstance(rows, list):
                raise HTTPException(status_code=400, detail="JSON body must be an array of transaction objects")
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}")
    else:
        # Parse CSV
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)

    imported = 0
    failed = 0
    errors: List[Dict[str, Any]] = []

    # Build a quick category id lookup
    valid_cat_ids = {r[0] for r in db.query(Category.id).all()}

    for idx, row in enumerate(rows):
        try:
            raw_cat = row.get("category_id")
            cat_id = int(raw_cat) if raw_cat not in (None, "", "null") else None
            if cat_id is not None and cat_id not in valid_cat_ids:
                cat_id = None  # silently drop unknown categories

            txn = Transaction(
                date=_parse_date(row.get("date")),
                description=str(row.get("description", "")).strip() or "Imported transaction",
                amount=float(row.get("amount", 0)),
                currency=str(row.get("currency", "USD")).upper()[:3],
                category_id=cat_id,
                subcategory=row.get("subcategory") or None,
                vendor=row.get("vendor") or None,
                payment_method=row.get("payment_method") or None,
                is_business=_parse_bool(row.get("is_business", True)),
                tax_deductible=_parse_bool(row.get("tax_deductible", False)),
                notes=row.get("notes") or None,
                receipt_url=row.get("receipt_url") or None,
                source="import",
            )
            db.add(txn)
            imported += 1
        except Exception as exc:
            failed += 1
            errors.append({"row": idx + 1, "error": str(exc), "data": dict(row)})

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error during import: {exc}")

    return ImportResult(imported=imported, failed=failed, errors=errors)


# ---------------------------------------------------------------------------
# Classify endpoint  — keyword matching
# ---------------------------------------------------------------------------

@router.post("/classify", response_model=ClassifyResponse)
def classify_transaction(
    data: ClassifyRequest,
    db: Session = Depends(get_db),
    _: str = Depends(get_api_key),
):
    """
    Suggest a category for a transaction based on keyword matching against
    its description and vendor.
    """
    search_text = " ".join(
        filter(None, [data.description, data.vendor])
    ).lower()

    match_count, best_name = _classify_text(search_text)

    if not best_name or match_count == 0:
        # Default to Uncategorized
        uncat = db.query(Category).filter(Category.name == "Uncategorized").first()
        return ClassifyResponse(
            category_id=uncat.id if uncat else None,
            category_name="Uncategorized",
            tax_category="pending_review",
            confidence=0.0,
            match_count=0,
        )

    cat = db.query(Category).filter(Category.name == best_name).first()
    # Confidence: capped at 1.0, rises with match count
    confidence = round(min(1.0, match_count / 3), 2)

    return ClassifyResponse(
        category_id=cat.id if cat else None,
        category_name=best_name,
        tax_category=cat.tax_category if cat else None,
        confidence=confidence,
        match_count=match_count,
    )
