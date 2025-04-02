# models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, index=True)
    photo_url = Column(String)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)  # Could be linked to the User table with a ForeignKey
    package_code = Column(String, nullable=False)
    order_id = Column(String, unique=True, index=True)  # Order id returned by the API
    qr_code = Column(String)  # URL or base64 string for the QR code
    status = Column(String, default="initiated")  # e.g., initiated, confirmed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print(f"[DEBUG] New User instance created: {kwargs}")
