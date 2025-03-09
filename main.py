from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from dotenv import load_dotenv
from database.database import engine
from database import models
from routers import chat

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("api_logs.log")
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Create FastAPI app with detailed metadata
app = FastAPI(
    title="Varanasi Chatbot API",
    description="""
    API for interacting with the Varanasi Chatbot (Shivendra).
    This API processes natural language queries about Varanasi and returns 
    informative responses along with relevant sources and images.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware with proper security settings
allowed_origins = [
    os.getenv("FRONTEND_URL", "https://kashi-frontend.vercel.app"),
    "http://localhost:3000",  # For local development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=3600,
)

# Health check endpoint
@app.get("/")
async def root():
    return {"status": "ok", "message": "Varanasi Chatbot API is running"}

# Include chat router
app.include_router(chat.router)

# Make sure the app is directly accessible as a module attribute
__all__ = ['app']