from sqlalchemy import Column, Integer, String, Boolean, Date, Time
from app.database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)
    type = Column(String, default="task")
    priority = Column(String, default="media")

    date = Column(Date, nullable=True)
    time = Column(Time, nullable=True)
    recurrence = Column(String, nullable=True)

    completed = Column(Boolean, default=False)
    last_completed_date = Column(Date, nullable=True)

    streak = Column(Integer, default=0)
    total_completions = Column(Integer, default=0)

    archived = Column(Boolean, default=False)
    remind_before = Column(Integer, default=60)