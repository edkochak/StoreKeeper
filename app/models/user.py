from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
    chat_id = Column(Integer, unique=True, nullable=True)

    store = relationship("Store", back_populates="managers")
    revenues = relationship("Revenue", back_populates="manager")
