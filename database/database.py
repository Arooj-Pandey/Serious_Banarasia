from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
import certifi

load_dotenv()

# Get database URL from environment variables or use Neon PostgreSQL connection string as default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_thI6dCeZ1bma@ep-tiny-king-a80g8ktf-pooler.eastus2.azure.neon.tech/neondb")

# Create SQLAlchemy engine with SSL configuration
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "sslmode": "verify-full",
        "sslcert": None,  # Let psycopg2 use the system's default certificates
        "sslkey": None,
        "sslrootcert": certifi.where()
    }
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for database models
Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()