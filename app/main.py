import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, SessionLocal, engine
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
