# init_db.py
from db import Base, engine
from models import *

def init_database():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully.")

if __name__ == "__main__":
    init_database()