import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. Build the Absolute Path
# Get the directory where THIS file (db.py) is located (e.g., .../Schedule-Assistant/app)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Go up one level to the Project Root (e.g., .../Schedule-Assistant)
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# Force the database to live in the Root folder
DB_PATH = os.path.join(PROJECT_ROOT, "schedule_ai.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# 2. Create the Engine
# echo=False stops the console from being flooded with text
engine = create_engine(DATABASE_URL, echo=False)

Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

print(f"🔵 Database connected at: {DB_PATH}")