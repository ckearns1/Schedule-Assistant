# think about an archateture - think at a high level and how the software is going to work together
# focus on different pieces like the agent piece or the interface.
# oLamma is an api, can download models into it. you can use oLama.
# Will need a key and to figure out what AI to use. oLama or gpt +\
#strt with system archeteture and a diagram for next week. LLang is a software lib for building agents.
# ORM classes (schema you posted)

#imports
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, Time
from sqlalchemy.orm import relationship
from db import Base

class PreferenceType():
    cantWork = "unavailable"
    ratherNot = "available but would prefer to avoid"
    favorite = "want to work"

class Employee(Base):
    __tablename__ = "employees"

    employee_id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    preferences = Column(String)  # e.g., JSON string or summary text

    # Relationships
    schedules = relationship("DraftSchedule", back_populates="employee")
    interactions = relationship("AgentInteraction", back_populates="employee")

class Agent(Base):
    #Represents the AI scheduling agent with versioning and status tracking.
    #Tracks which AI instance made a proposal or adjustment.
    __tablename__ = "agents"

    agent_id = Column(Integer, primary_key=True)
    version = Column(String)
    status = Column(String)

    proposals = relationship("AgentProposal", back_populates="agent")
    interactions = relationship("AgentInteraction", back_populates="agent")

class AvailabilityPreference(Base):
    __tablename__ = "availability_preferences"
    pref_id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"))
    day_of_week = Column(String)
    start_time = Column(Time)
    end_time = Column(Time)
    preference = Column(String)
    notes = Column(String)
    employee = relationship("Employee")

class AgentInteraction(Base):
    #Logs AI–employee interactions around scheduling, including times, confidence score, and status.
    #Provides a history of how schedules were generated or modified.
    __tablename__ = "agent_interactions"

    interaction_id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"))
    agent_id = Column(Integer, ForeignKey("agents.agent_id"))
    date = Column(Date)
    start_time = Column(Time)
    end_time = Column(Time)
    confidence_score = Column(Float)
    status = Column(String)

    employee = relationship("Employee", back_populates="interactions")
    agent = relationship("Agent", back_populates="interactions")

class DraftSchedule():
    # Temporary schedule assignments tied to employees.
    # Holds shift details with confidence and status until finalized.
    __tablename__ = "draft_schedules"

    schedule_id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"))
    date = Column(Date)
    start_time = Column(Time)
    end_time = Column(Time)
    confidence_score = Column(Float)
    status = Column(String)

    employee = relationship("Employee", back_populates="schedules")

class AgentProposal():
    # Represents proposed schedule changes suggested by the AI agent.
    # Acts as a candidate plan for review before becoming official.
    __tablename__ = "agent_proposals"

    proposal_id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.agent_id"))
    summary = Column(String)
    confidence_score = Column(Float)
    status = Column(String)

    agent = relationship("Agent", back_populates="proposals")