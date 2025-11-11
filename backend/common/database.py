from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", 
                         "postgresql://leobrain:leobrain_dev@localhost:5432/leobrain")

engine = create_engine(DATABASE_URL, echo=True)

def init_db():
    """Initialize database tables
    """
    SQLModel.metadata.create_all(engine)
    

def get_session() -> Generator[Session, None, None]:
    """Get database session generator
    """
    with Session(engine) as session:
        yield session