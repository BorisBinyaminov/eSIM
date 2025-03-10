# models.py
from sqlalchemy import Column, Integer, String
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, index=True)
    photo_url = Column(String)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print(f"[DEBUG] New User instance created: {kwargs}")
