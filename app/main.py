import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import Base, SessionLocal, engine, get_db
from app.models import Transaction, Category, Account, Budget
from app.routers import accounts, budgets, categories, dashboard, reports, transactions


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup
    Base.metadata.create_all(bind=engine)

    # Seed default data
    db = SessionLocal()
    try:
        from app.seed import seed_all
        seed_all(db)
    finally:
        db.close()

    yield  # app runs here


app = FastAPI(
    title="Finance Pro",
    description=(
        "Business expense tracker and financial reporting API.\n\n"
        "**Authentication:** All endpoints (except `/health`) require an `X-API-Key` header "
        "matching the `GDEV_API_TOKEN` environment variable."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Root dashboard — no auth required
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root_dashboard(db: Session = Depends(get_db)):
    tx_count = db.query(func.count(Transaction.id)).scalar() or 0
    cat_count = db.query(func.count(Category.id)).scalar() or 0
    acct_count = db.query(func.count(Account.id)).scalar() or 0
    budget_count = db.query(func.count(Budget.id)).scalar() or 0
    income = float(db.query(func.coalesce(func.sum(Transaction.amount), 0)).join(Category, Transaction.category_id == Category.id).filter(Category.type == "income").scalar() or 0)
    expenses = abs(float(db.query(func.coalesce(func.sum(Transaction.amount), 0)).join(Category, Transaction.category_id == Category.id).filter(Category.type == "expense").scalar() or 0))
    recent = db.query(Transaction).order_by(Transaction.date.desc(), Transaction.id.desc()).limit(8).all()
    rows = ""
    for t in recent:
        cat = t.category_obj.name if t.category_obj else "—"
        amt = float(t.amount)
        color = "#34c759" if amt > 0 and t.category_obj and t.category_obj.type == "income" else "#e74c3c"
        rows += f'<tr><td>{t.date}</td><td>{t.description}</td><td>{cat}</td><td>{t.vendor or "—"}</td><td style="color:{color};font-weight:600">${abs(amt):,.2f}</td></tr>'
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Finance Pro</title>
<style>
:root{{--primary:#4f8ef7;--success:#34c759;--warning:#f5a623;--danger:#e74c3c;--bg:#1a1f36;--bg-light:#f5f7fa;--card:#fff;--text:#2c3e50;--muted:#7f8c9b;--border:#e1e5eb}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:system-ui,-apple-system,sans-serif;background:var(--bg-light);color:var(--text);display:flex;min-height:100vh}}
.sidebar{{width:240px;background:var(--bg);color:#fff;display:flex;flex-direction:column;flex-shrink:0}}
.logo{{padding:1.5rem;font-size:1.4rem;font-weight:700}}
.nav-links{{flex:1;padding:0 1rem}}
.nav-link{{display:block;padding:.75rem 1rem;color:#cbd5e1;text-decoration:none;border-radius:6px;margin-bottom:.25rem}}
.nav-link:hover,.nav-link.active{{background:rgba(255,255,255,.15);color:#fff}}
.main{{flex:1;padding:2rem;overflow-y:auto}}
h1{{font-size:1.8rem;margin-bottom:1.5rem}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;margin-bottom:2rem}}
.card{{background:var(--card);border-radius:10px;padding:1.5rem;border:1px solid var(--border)}}
.card .label{{font-size:.85rem;color:var(--muted);margin-bottom:.25rem}}
.card .value{{font-size:1.6rem;font-weight:700}}
.card .value.green{{color:var(--success)}}
.card .value.red{{color:var(--danger)}}
.card .value.blue{{color:var(--primary)}}
table{{width:100%;border-collapse:collapse;background:var(--card);border-radius:10px;overflow:hidden;border:1px solid var(--border)}}
th,td{{padding:.75rem 1rem;text-align:left;border-bottom:1px solid var(--border)}}
th{{background:var(--bg);color:#fff;font-weight:600;font-size:.85rem;text-transform:uppercase;letter-spacing:.5px}}
tr:last-child td{{border-bottom:none}}
.section-title{{font-size:1.1rem;font-weight:600;margin-bottom:1rem}}
a.api-link{{display:inline-block;margin-top:1rem;padding:.5rem 1rem;background:var(--primary);color:#fff;border-radius:6px;text-decoration:none;font-size:.9rem}}
</style></head><body>
<div class="sidebar">
  <div class="logo">Finance Pro</div>
  <div class="nav-links">
    <a href="/" class="nav-link active">Dashboard</a>
    <a href="/docs" class="nav-link">API Docs</a>
  </div>
</div>
<div class="main">
  <h1>Dashboard</h1>
  <div class="cards">
    <div class="card"><div class="label">Transactions</div><div class="value blue">{tx_count}</div></div>
    <div class="card"><div class="label">Total Income</div><div class="value green">${income:,.2f}</div></div>
    <div class="card"><div class="label">Total Expenses</div><div class="value red">${expenses:,.2f}</div></div>
    <div class="card"><div class="label">Net</div><div class="value {'green' if income-expenses>=0 else 'red'}">${income-expenses:,.2f}</div></div>
    <div class="card"><div class="label">Categories</div><div class="value">{cat_count}</div></div>
    <div class="card"><div class="label">Accounts</div><div class="value">{acct_count}</div></div>
    <div class="card"><div class="label">Budgets</div><div class="value">{budget_count}</div></div>
  </div>
  <div class="section-title">Recent Transactions</div>
  <table><thead><tr><th>Date</th><th>Description</th><th>Category</th><th>Vendor</th><th>Amount</th></tr></thead><tbody>{rows if rows else '<tr><td colspan="5" style="text-align:center;color:var(--muted)">No transactions yet</td></tr>'}</tbody></table>
  <a href="/docs" class="api-link">API Documentation &rarr;</a>
</div></body></html>"""


# ---------------------------------------------------------------------------
# Health check — no auth required
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"], include_in_schema=True)
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# API v1 routers
# ---------------------------------------------------------------------------

PREFIX = "/api/v1"

app.include_router(transactions.router, prefix=PREFIX)
app.include_router(categories.router,  prefix=PREFIX)
app.include_router(accounts.router,    prefix=PREFIX)
app.include_router(budgets.router,     prefix=PREFIX)
app.include_router(reports.router,     prefix=PREFIX)
app.include_router(dashboard.router,   prefix=PREFIX)
