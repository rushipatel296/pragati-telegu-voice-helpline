from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite database file will be created as pragati.db in your project root
SQLALCHEMY_DATABASE_URL = "sqlite:///./pragati.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Required for SQLite in multithreaded FastAPI apps
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# FastAPI Dependency to handle DB session lifecycle (opens and closes connections per request)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()