from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import relationship
from app.core.database import Base


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    plan = Column(Float, nullable=False, default=0.0)  # индивидуальный план магазина

    revenues = relationship("Revenue", back_populates="store")  # связь с выручкой
    managers = relationship("User", back_populates="store")  # связь с менеджерами
