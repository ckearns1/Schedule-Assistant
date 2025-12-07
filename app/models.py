from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, Time, JSON, Text
from sqlalchemy.orm import relationship
# We use 'app.db' so it works when running scripts from the main folder
from app.db import Base


class Employee(Base):
    __tablename__ = "employees"

    employee_id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    preferences = Column(String)  # e.g., JSON string or summary text

    # Relationships
    schedules = relationship("ScheduleEntry", back_populates="employee")


class Schedule(Base):
    """
    Represents a complete schedule version (e.g., 'Spring 2025 Draft').
    """
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True)
    version_name = Column(String, nullable=False)  # e.g., "Spring 2025 Initial Import"
    status = Column(String, default="draft")  # 'draft', 'final', 'archived'

    # Relationships
    entries = relationship("ScheduleEntry", back_populates="schedule")


class ScheduleEntry(Base):
    """
    Represents a single shift assignment (e.g., Connor works Monday at 9am).
    """
    __tablename__ = "schedule_entries"

    id = Column(Integer, primary_key=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=False)

    day_of_week = Column(String, nullable=False)  # e.g. "Monday"
    hour = Column(Integer, nullable=False)  # 0-23 (24-hour format)

    # Relationships
    schedule = relationship("Schedule", back_populates="entries")
    employee = relationship("Employee", back_populates="schedules")