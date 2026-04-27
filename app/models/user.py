from sqlalchemy import BigInteger, Boolean, Column, String

from db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), default="user", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
