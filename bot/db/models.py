from sqlalchemy import (
    Column, BigInteger, String, Boolean, 
    DateTime, Integer, Text, func
)
from .base import Base


class User(Base):
    """Foydalanuvchilar modeli"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    is_admin = Column(Boolean, default=False)
    is_vip = Column(Boolean, default=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    last_active = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<User {self.telegram_id} {self.username}>"


class Code(Base):
    """Kodlar modeli"""
    __tablename__ = "codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    is_used = Column(Boolean, default=False)
    used_by = Column(BigInteger, nullable=True)  # telegram_id
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    used_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Code {self.code} used={self.is_used}>"


class Payment(Base):
    """To'lovlar modeli"""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    amount = Column(Integer, nullable=False)  # so'mda
    status = Column(String(50), default="pending")  # pending, paid, cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Payment {self.id} user={self.user_id} status={self.status}>"
