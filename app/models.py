from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, Date, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    type = Column(String(20), nullable=False)          # income / expense
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    tax_category = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)

    parent = relationship("Category", remote_side=[id], back_populates="children")
    children = relationship("Category", back_populates="parent")
    transactions = relationship("Transaction", back_populates="category_obj")
    budgets = relationship("Budget", back_populates="category_obj")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)          # checking/savings/credit_card/cash
    institution = Column(String(255), nullable=True)
    last_four = Column(String(4), nullable=True)
    currency = Column(String(3), default="USD")
    balance = Column(Numeric(14, 2), default=0)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    description = Column(String(500), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(3), default="USD")
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    subcategory = Column(String(255), nullable=True)
    vendor = Column(String(255), nullable=True)
    payment_method = Column(String(100), nullable=True)
    is_business = Column(Boolean, default=True)
    tax_deductible = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    receipt_url = Column(String(500), nullable=True)
    source = Column(String(20), default="manual")      # manual / import
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    category_obj = relationship("Category", back_populates="transactions")

    @property
    def category_name(self):
        return self.category_obj.name if self.category_obj else None

    @property
    def tax_category(self):
        return self.category_obj.tax_category if self.category_obj else None


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    period = Column(String(20), nullable=False)        # monthly / quarterly / annual
    amount = Column(Numeric(14, 2), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=True)             # 1-12; null for annual/quarterly

    category_obj = relationship("Category", back_populates="budgets")

    @property
    def category_name(self):
        return self.category_obj.name if self.category_obj else None


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    parameters = Column(JSON, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)
