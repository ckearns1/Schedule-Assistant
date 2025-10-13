# DB setup (SQLAlchemy)
# db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# SQLite database file (auto-created in project root)
DATABASE_URL = "sqlite:///schedule_ai.db"

# Create database engine
engine = create_engine(DATABASE_URL, echo=True)

# Base class for ORM models
Base = declarative_base()

# Session factory (used to interact with DB)
SessionLocal = sessionmaker(bind=engine)