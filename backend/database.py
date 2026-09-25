import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

# Ensure tests or local dev can override this
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://factory_user:factory_password@localhost:5432/factory_db"
)

# Set pool_pre_ping to check connection liveness
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
