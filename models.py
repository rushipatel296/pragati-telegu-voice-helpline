from sqlalchemy import Column, String, JSON, DateTime
from datetime import datetime, timezone
from database import Base

class UserSessionModel(Base):
    __tablename__ = "user_sessions"

    session_id = Column(String, primary_key=True, index=True)
    profile = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc)
    )