from sqlalchemy import Column, Integer, Date, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Revenue(Base):
    __tablename__ = "revenues"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    store = relationship("Store", back_populates="revenues")
    manager = relationship("User", back_populates="revenues")
