from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # 'admin' или 'manager'
    store_id = Column(
        Integer, ForeignKey("stores.id"), nullable=True
    )  # привязка к магазину (только для менеджеров)

    store = relationship("Store", back_populates="managers")  # связь с магазином
    revenues = relationship("Revenue", back_populates="manager")
