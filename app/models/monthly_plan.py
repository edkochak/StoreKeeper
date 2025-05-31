from sqlalchemy import Column, Integer, Float, ForeignKey, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class MonthlyPlan(Base):
    __tablename__ = "monthly_plans"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    month_year = Column(Date, nullable=False)
    plan_amount = Column(Float, nullable=False, default=0.0)

    store = relationship("Store", back_populates="monthly_plans")

    __table_args__ = (
        UniqueConstraint("store_id", "month_year", name="_store_month_plan_uc"),
    )
