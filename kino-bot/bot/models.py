from sqlalchemy import Column, BigInteger, String, Integer, Boolean, DateTime, Text
from sqlalchemy.sql import func
from bot.database import Base

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    is_premium = Column(Boolean, default=False)
    premium_expire = Column(DateTime, nullable=True)
    daily_count = Column(Integer, default=0)
    last_reset = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())

class Movie(Base):
    __tablename__ = 'movies'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True, nullable=False, index=True)  # Masalan: "4587"
    channel_id = Column(BigInteger, nullable=False)  # Kanal ID
    message_id = Column(Integer, nullable=False)      # Message ID
    title = Column(String, nullable=True)             # Kino nomi
    category = Column(String, nullable=True)          # Action/Drama...
    views = Column(Integer, default=0)                # Ko'rilgan soni
    created_at = Column(DateTime, server_default=func.now())

class Payment(Base):
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    amount = Column(Integer, nullable=False)
    plan = Column(String, nullable=False)  # "1_month", "3_month", "lifetime"
    payment_id = Column(String, unique=True)
    status = Column(String, default="pending")  # pending, success, failed
    created_at = Column(DateTime, server_default=func.now())