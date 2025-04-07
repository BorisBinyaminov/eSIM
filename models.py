from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Text, ForeignKey
from sqlalchemy.sql import func
from database import Base
from sqlalchemy import UniqueConstraint

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, index=True)
    photo_url = Column(String)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print(f"[DEBUG] New User instance created: {kwargs}")

class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("order_id", "iccid", name="uq_order_iccid"),)
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic order info
    user_id = Column(String, index=True)  # Consider linking to the User table via a ForeignKey.
    package_code = Column(String, nullable=False)
    order_id = Column(String, index=True)  # Order number returned by the API.
    transaction_id = Column(String, index=True)  # External transaction ID from payment.
    iccid = Column(String, nullable=True)                     # ICCID from the allocated profile.
    
    # Purchase details
    count = Column(Integer, default=1)         # Number of packages/days ordered.
    period_num = Column(Integer, nullable=True)  # For daily plans: number of days.
    price = Column(Integer)                      # Cost price (what you pay) in the smallest currency unit.
    retail_price = Column(Integer)               # Price charged to the user.
    qr_code = Column(String)                     # URL or base64 string for the QR code.
    status = Column(String, default="initiated") # e.g., initiated, confirmed, failed.
    details = Column(Text, nullable=True)        # Optional raw API response or additional info.
    
    # Fields returned from the Query All Allocated Profiles API
    esim_status = Column(String)   # esimStatus (e.g., RELEASED, ENABLED, etc.)
    smdp_status = Column(String)   # SM-DP+ status.
    expired_time = Column(DateTime(timezone=True))  # Expiration time.
    total_volume = Column(BigInteger)      # Total data volume in bytes.
    total_duration = Column(Integer)       # Total valid period (days).
    order_usage = Column(BigInteger)       # Volume used in bytes.
    esim_list = Column(Text)               # The complete list of allocated eSIM profiles (as JSON string).
    package_list = Column(Text)            # The packageList details (as JSON string).
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print(f"[DEBUG] New Order instance created: {kwargs}")
