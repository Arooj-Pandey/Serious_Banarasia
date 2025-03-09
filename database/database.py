from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
import certifi
import time
import logging
from sqlalchemy.pool import QueuePool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Get database URL from environment variables or use Neon PostgreSQL connection string as default
DATABASE_URL = os.getenv("DATABASE_URL")

# Create SQLAlchemy engine with more resilient configuration
engine = create_engine(
    DATABASE_URL,
    pool_size=5,  # Start with 5 connections
    max_overflow=10,  # Allow up to 10 additional connections
    pool_timeout=30,  # Wait up to 30 seconds for a connection
    pool_recycle=1800,  # Recycle connections after 30 minutes
    pool_pre_ping=True,  # Verify connections before using them
    connect_args={
        "sslmode": "require",  # Less strict than verify-full but still secure
        "connect_timeout": 10,  # Connection timeout in seconds
        "keepalives": 1,  # Enable TCP keepalives
        "keepalives_idle": 60,  # Seconds between keepalives
        "keepalives_interval": 10,  # Seconds between keepalive probes
        "keepalives_count": 5  # Number of keepalive probes
    }
)

# Add connection event listeners for better debugging
@event.listens_for(engine, "connect")
def connect(dbapi_connection, connection_record):
    logger.info("Database connection established")

@event.listens_for(engine, "checkout")
def checkout(dbapi_connection, connection_record, connection_proxy):
    logger.info("Database connection checked out from pool")

@event.listens_for(engine, "checkin")
def checkin(dbapi_connection, connection_record):
    logger.info("Database connection returned to pool")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for database models
Base = declarative_base()

# Dependency to get database session with retry logic
def get_db():
    db = SessionLocal()
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            # Test the connection with a simple query using text()
            db.execute(text("SELECT 1"))
            # If successful, yield the db session
            yield db
            break
        except Exception as e:
            retry_count += 1
            logger.warning(f"Database connection error (attempt {retry_count}/{max_retries}): {str(e)}")
            
            if retry_count >= max_retries:
                logger.error(f"Failed to connect to database after {max_retries} attempts")
                # Close the current session
                db.close()
                # Raise the exception to be handled by FastAPI
                raise
            
            # Wait before retrying (exponential backoff)
            time.sleep(2 ** retry_count)
            # Create a new session for the retry
            db.close()
            db = SessionLocal()
    
    # Always close the session when done
    try:
        db.close()
    except:
        pass