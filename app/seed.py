"""Seed the database with default categories and sample records."""
from datetime import date, datetime
from sqlalchemy.orm import Session

from app.models import Category, Account, Transaction, Budget, Report


DEFAULT_CATEGORIES = [
    # ---- Expense categories ----
    {"name": "Software & SaaS",        "type": "expense", "tax_category": "business_expense",    "description": "Subscriptions to software tools and SaaS products"},
    {"name": "Cloud Infrastructure",   "type": "expense", "tax_category": "business_expense",    "description": "Hosting, compute, storage, and CDN costs"},
    {"name": "Professional Services",  "type": "expense", "tax_category": "business_expense",    "description": "Legal, accounting, consulting, and contractor fees"},
    {"name": "Travel & Transportation","type": "expense", "tax_category": "business_expense",    "description": "Flights, hotels, rideshare, and transit"},
    {"name": "Meals & Entertainment",  "type": "expense", "tax_category": "meals_entertainment", "description": "Business meals and entertainment (50% deductible)"},
    {"name": "Office Supplies",        "type": "expense", "tax_category": "business_expense",    "description": "Stationery, printer supplies, and general office items"},
    {"name": "Marketing & Advertising","type": "expense", "tax_category": "business_expense",    "description": "Paid ads, SEO, and promotional spend"},
    {"name": "Insurance",              "type": "expense", "tax_category": "business_expense",    "description": "Business liability, E&O, and other insurance premiums"},
    {"name": "Rent & Utilities",       "type": "expense", "tax_category": "business_expense",    "description": "Office rent, electricity, internet, and phone"},
    {"name": "Education & Training",   "type": "expense", "tax_category": "business_expense",    "description": "Courses, conferences, books, and certifications"},
    {"name": "Hardware & Equipment",   "type": "expense", "tax_category": "depreciation",        "description": "Laptops, monitors, servers, and other depreciable equipment"},
    {"name": "Health & Medical",       "type": "expense", "tax_category": "medical_expense",     "description": "Medical expenses and health-related costs"},
    {"name": "Personal",               "type": "expense", "tax_category": "not_deductible",      "description": "Non-business personal expenses"},
    {"name": "Uncategorized",          "type": "expense", "tax_category": "pending_review",      "description": "Transactions awaiting category assignment"},
    # ---- Income categories ----
    {"name": "Revenue",                "type": "income",  "tax_category": "income",              "description": "Primary business revenue"},
    {"name": "Consulting Income",      "type": "income",  "tax_category": "income",              "description": "Income from consulting engagements"},
    {"name": "Other Income",           "type": "income",  "tax_category": "income",              "description": "Miscellaneous business income"},
]


def _category_by_name(db: Session, name: str) -> Category | None:
    return db.query(Category).filter(Category.name == name).first()


def seed_all(db: Session) -> None:
    """Insert seed data only when the tables are empty."""
    if db.query(Category).count() > 0:
        return  # already seeded

    # --- Categories ---
    cat_map: dict[str, Category] = {}
    for data in DEFAULT_CATEGORIES:
        cat = Category(**data)
        db.add(cat)
        db.flush()  # get the id before commit
        cat_map[cat.name] = cat
    db.commit()

    # --- Accounts ---
    checking = Account(
        name="Business Checking",
        type="checking",
        institution="Chase Bank",
        last_four="4821",
        currency="USD",
        balance=48_320.50,
    )
    credit = Account(
        name="Business Credit Card",
        type="credit_card",
        institution="American Express",
        last_four="9003",
        currency="USD",
        balance=-3_412.75,
    )
    db.add_all([checking, credit])
    db.commit()

    # --- Sample transactions ---
    software_id = cat_map["Software & SaaS"].id
    cloud_id    = cat_map["Cloud Infrastructure"].id
    travel_id   = cat_map["Travel & Transportation"].id
    meals_id    = cat_map["Meals & Entertainment"].id
    marketing_id = cat_map["Marketing & Advertising"].id
    hardware_id = cat_map["Hardware & Equipment"].id
    revenue_id  = cat_map["Revenue"].id
    consulting_id = cat_map["Consulting Income"].id
    prof_id     = cat_map["Professional Services"].id
    office_id   = cat_map["Office Supplies"].id

    transactions = [
        Transaction(date=date(2025, 1, 3),  description="GitHub Teams subscription",        amount=-99.00,    currency="USD", category_id=software_id,  vendor="GitHub",          payment_method="credit_card", is_business=True, tax_deductible=True, source="manual"),
        Transaction(date=date(2025, 1, 5),  description="AWS EC2 and S3 usage",             amount=-1_234.56, currency="USD", category_id=cloud_id,     vendor="Amazon Web Services", payment_method="credit_card", is_business=True, tax_deductible=True, source="manual"),
        Transaction(date=date(2025, 1, 8),  description="Notion Teams annual plan",         amount=-960.00,   currency="USD", category_id=software_id,  vendor="Notion",          payment_method="credit_card", is_business=True, tax_deductible=True, source="manual"),
        Transaction(date=date(2025, 1, 10), description="Client project invoice #1001",     amount=12_500.00, currency="USD", category_id=revenue_id,   vendor="Acme Corp",       payment_method="bank_transfer", is_business=True, tax_deductible=False, source="manual"),
        Transaction(date=date(2025, 1, 14), description="Flight to SF for client meeting",  amount=-487.00,   currency="USD", category_id=travel_id,    vendor="United Airlines", payment_method="credit_card", is_business=True, tax_deductible=True, source="manual"),
        Transaction(date=date(2025, 1, 15), description="Team lunch at Nobu",               amount=-342.50,   currency="USD", category_id=meals_id,     vendor="Nobu Restaurant", payment_method="credit_card", is_business=True, tax_deductible=True, notes="Q1 team lunch", source="manual"),
        Transaction(date=date(2025, 1, 18), description="Google Ads campaign - January",    amount=-2_100.00, currency="USD", category_id=marketing_id, vendor="Google Ads",      payment_method="credit_card", is_business=True, tax_deductible=True, source="manual"),
        Transaction(date=date(2025, 1, 22), description="MacBook Pro for developer",        amount=-2_499.00, currency="USD", category_id=hardware_id,  vendor="Apple Store",     payment_method="credit_card", is_business=True, tax_deductible=True, source="manual"),
        Transaction(date=date(2025, 1, 28), description="Legal retainer - Smith & Partners",amount=-1_500.00, currency="USD", category_id=prof_id,      vendor="Smith & Partners",payment_method="bank_transfer", is_business=True, tax_deductible=True, source="manual"),
        Transaction(date=date(2025, 1, 31), description="Office supplies from Staples",     amount=-128.45,   currency="USD", category_id=office_id,    vendor="Staples",         payment_method="credit_card", is_business=True, tax_deductible=True, source="manual"),
        Transaction(date=date(2025, 2, 3),  description="Consulting engagement - WidgetCo",amount=8_750.00,  currency="USD", category_id=consulting_id, vendor="WidgetCo",        payment_method="bank_transfer", is_business=True, tax_deductible=False, source="manual"),
        Transaction(date=date(2025, 2, 5),  description="Vercel Pro subscription",          amount=-20.00,    currency="USD", category_id=cloud_id,     vendor="Vercel",          payment_method="credit_card", is_business=True, tax_deductible=True, source="manual"),
        Transaction(date=date(2025, 2, 10), description="Figma Professional annual",        amount=-576.00,   currency="USD", category_id=software_id,  vendor="Figma",           payment_method="credit_card", is_business=True, tax_deductible=True, source="manual"),
        Transaction(date=date(2025, 2, 15), description="Hotel in San Francisco",           amount=-875.00,   currency="USD", category_id=travel_id,    vendor="Marriott Hotels", payment_method="credit_card", is_business=True, tax_deductible=True, source="manual"),
        Transaction(date=date(2025, 2, 20), description="Client dinner - Q1 strategy",      amount=-215.80,   currency="USD", category_id=meals_id,     vendor="Nobu Restaurant", payment_method="credit_card", is_business=True, tax_deductible=True, notes="Client dinner with Acme Corp", source="manual"),
        Transaction(date=date(2025, 3, 1),  description="Mystery charge XYZ-CORP",          amount=-450.00,   currency="USD", category_id=None,         vendor="XYZ Corp",        payment_method="credit_card", is_business=True, tax_deductible=False, source="import"),
        Transaction(date=date(2025, 3, 5),  description="Unknown payment ref #84921",       amount=-120.00,   currency="USD", category_id=None,         vendor=None,              payment_method="credit_card", is_business=False, tax_deductible=False, source="import"),
    ]
    db.add_all(transactions)
    db.commit()

    # --- Sample budgets ---
    budgets = [
        Budget(category_id=software_id,  period="monthly",  amount=2_000.00, year=2025, month=None),
        Budget(category_id=cloud_id,     period="monthly",  amount=3_000.00, year=2025, month=None),
        Budget(category_id=marketing_id, period="quarterly", amount=10_000.00, year=2025, month=None),
        Budget(category_id=travel_id,    period="annual",   amount=15_000.00, year=2025, month=None),
        Budget(category_id=meals_id,     period="monthly",  amount=800.00,   year=2025, month=None),
    ]
    db.add_all(budgets)
    db.commit()

    # --- Sample saved report ---
    report = Report(
        name="2025 Q1 Tax Summary",
        type="tax_report",
        parameters={"year": 2025, "quarter": 1},
        generated_at=datetime(2025, 4, 1, 9, 0, 0),
    )
    db.add(report)
    db.commit()
