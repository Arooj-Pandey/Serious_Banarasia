from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os
import sys
import logging
import time
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from pathlib import Path

# Add parent directory to path so we can import from other modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Import components from the existing chatbot
from models.factory import ModelFactory
from translator.queryTranslator import Translator as QueryTranslator
from keywords_Segregator.segregator import Segregator as KeywordsSegregator
from queryRouter.router import QueryRouter
from utils.responseFormater import ResponseFormatter
from utility.final_response import generate_final_prompt

from fastapi import Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from database.database import get_db, engine
from database import models, crud
from auth.auth import oauth, create_access_token, get_current_user
import uuid
from starlette.middleware.sessions import SessionMiddleware

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

# Add session middleware with secure settings
app.add_middleware(
    SessionMiddleware, 
    secret_key=os.getenv("SECRET_KEY", "your-session-secret-key"),
    max_age=3600,  # 1 hour
    same_site="lax",  # Protects against CSRF while allowing OAuth
    https_only=True  # Ensure cookies only sent over HTTPS
)

# Define request and response models with detailed documentation
class ChatRequest(BaseModel):
    query: str = Field(..., description="The user's question or message to the chatbot")
    user_id: Optional[str] = Field(None, description="Unique identifier for the user session")

class Source(BaseModel):
    domain: str = Field(..., description="Domain name of the source")
    link: str = Field(..., description="URL of the source")
    snippet: str = Field(..., description="Text snippet from the source")

class Image(BaseModel):
    url: str = Field(..., description="URL of the image")
    title: Optional[str] = Field(None, description="Title or description of the image")

class ChatResponse(BaseModel):
    response: str = Field(..., description="The chatbot's response to the user's query")
    sources: List[Source] = Field(default_factory=list, description="List of sources referenced in the response")
    images: List[Image] = Field(default_factory=list, description="List of relevant images")
    processing_time: float = Field(..., description="Time taken to process the request in seconds")

# Create dependency for model initialization to handle errors better
def get_model():
    try:
        return ModelFactory.get_model("gemini", os.getenv("GEMINI_API_KEY"), "gemini-1.5-flash")
    except Exception as e:
        logger.error(f"Model initialization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI model initialization failed: {str(e)}")

# Create dependencies for other components
def get_translator():
    try:
        # Initialize translator with the required API key and model info
        return QueryTranslator(
            api_key=os.getenv("GEMINI_API_KEY"),
            model_type="gemini",
            model_name="gemini-1.5-flash",
            prompt_template_path=str(Path(__file__).parent / "prompts" / "translator" / "translator_prompt.txt")
        )
    except Exception as e:
        logger.error(f"Translator initialization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Query translator initialization failed: {str(e)}")

def get_segregator():
    try:
        # Initialize segregator with the required API key and model info
        return KeywordsSegregator(
            api_key=os.getenv("GEMINI_API_KEY"),
            model_type="gemini",
            model_name="gemini-1.5-flash",
            prompt_template_path=str(Path(__file__).parent / "prompts" / "query_router" / "query_keywords_seggregator.txt")
        )
    except Exception as e:
        logger.error(f"Segregator initialization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Keywords segregator initialization failed: {str(e)}")

# Cache for rate limiting and optimization
request_cache = {}

@app.get("/api/login/google")
async def login_google(request: Request):
    # Store the original referrer for post-login redirect
    request.session["referrer"] = str(request.headers.get("referer", os.getenv("FRONTEND_URL")))
    
    # Use configured redirect URI instead of dynamic one
    redirect_uri = f"{os.getenv('BACKEND_URL', 'https://your-backend-url.azurewebsites.net')}/api/auth/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)

# Google OAuth callback route
@app.get("/api/auth/callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")
        
        if not user_info:
            raise HTTPException(status_code=400, detail="Could not fetch user info")
        
        email = user_info["email"]
        name = user_info.get("name", "User")
        picture = user_info.get("picture")
        google_id = user_info.get("sub")
        
        # Check if user exists, create if not
        user = crud.get_user_by_email(db, email)
        if not user:
            user = crud.create_user(db, email=email, name=name, picture=picture, google_id=google_id)
        else:
            # Update existing user info
            user = crud.update_user(db, user.id, name=name, picture=picture, google_id=google_id)
        
        # Create access token
        access_token = create_access_token(data={"sub": email})
        
        # Get the original referrer or use default frontend URL
        frontend_url = request.session.get("referrer", os.getenv("FRONTEND_URL"))
        redirect_url = f"{frontend_url}/auth/callback?token={access_token}"
        
        # Clear the session
        request.session.clear()
        
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        logger.error(f"Auth callback error: {str(e)}")
        frontend_url = os.getenv("FRONTEND_URL")
        return RedirectResponse(f"{frontend_url}/auth/error?message=Authentication failed")

# Get user profile route
@app.get("/api/users/me", response_model=dict)
async def get_user_profile(current_user: models.User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "picture": current_user.picture
    }

# Add a protected endpoint to test authentication
@app.get("/api/protected")
async def protected_route(current_user: models.User = Depends(get_current_user)):
    return {"message": "This is a protected endpoint", "user": current_user.email}

@app.get("/")
async def root():
    """Health check endpoint to verify API is running"""
    return {"status": "online", "message": "Varanasi Chatbot API is running"}

@app.get("/api/health")
async def health_check():
    """Detailed health check endpoint with component status"""
    health_status = {
        "api": "healthy",
        "model": "unknown",
        "database": "not_applicable",
        "timestamp": time.time()
    }
    
    try:
        # Test model connectivity
        model = get_model()
        health_status["model"] = "healthy"
    except Exception as e:
        health_status["model"] = "unhealthy"
        health_status["model_error"] = str(e)
    
    return health_status

@app.post("/api/chat", response_model=ChatResponse)
async def process_chat(
    request: ChatRequest,
    current_user: models.User = Depends(get_current_user),
    model=Depends(get_model),
    translator=Depends(get_translator),
    segregator=Depends(get_segregator),
    db: Session = Depends(get_db)
):
    start_time = time.time()
    
    try:
        # Store user message
        crud.create_chat_message(
            db=db,
            user_id=current_user.id,
            message=request.query,
            sender='user'
        )
        
        user_query = request.query
        logger.info(f"Processing query for user {current_user.id}: {user_query}")
        
        # Your existing chat processing logic here...
        if len(user_query.split()) <= 8 and any(keyword in user_query.lower() for keyword in ["varanasi", "banaras", "kashi"]):
            restructured_query = user_query
            logger.info("Simple query detected, skipping translation")
        else:
            logger.info("Step 1: Starting query translation")
            restructured_query = translator.translate_query(user_query)
            logger.info(f"Step 1 complete: Query translated successfully")
        
        # Rest of your existing processing code...
        # After getting the AI response, store the bot's message
        
        ai_response = "Default response if processing fails"
        try:
            # Your existing response generation code
            keywords = segregator.keywords_seggregator(restructured_query)
            router = QueryRouter(serper_api_key=os.getenv("SERPER_API_KEY"))
            raw_results = router.route_keywords(keywords)
            formatter = ResponseFormatter(raw_results, max_content_length=2000)
            formatted_results = formatter.format_for_llm()
            ai_response = generate_final_prompt(formatted_results, user_query)
            
            # Store bot's response
            crud.create_chat_message(
                db=db,
                user_id=current_user.id,
                message=ai_response,
                sender='bot'
            )
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            ai_response = "I apologize, but I encountered an error processing your question. Please try again."
            crud.create_chat_message(
                db=db,
                user_id=current_user.id,
                message=ai_response,
                sender='bot'
            )
            
        processing_time = time.time() - start_time
        return ChatResponse(
            response=ai_response,
            sources=[],  # Your existing sources logic
            images=[],   # Your existing images logic
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.exception(f"Error processing chat: {str(e)}")
        processing_time = time.time() - start_time
        error_message = "I'm sorry, I encountered an error while processing your question. Please try again."
        
        # Store error message
        crud.create_chat_message(
            db=db,
            user_id=current_user.id,
            message=error_message,
            sender='bot'
        )
        
        return ChatResponse(
            response=error_message,
            sources=[],
            images=[],
            processing_time=processing_time
        )

@app.get("/api/chat/history")
async def get_chat_history(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50
):
    """Retrieve chat history for the authenticated user"""
    messages = crud.get_chat_messages(db, current_user.id, skip=skip, limit=limit)
    return messages

# Make sure the app is directly accessible as a module attribute
__all__ = ['app']

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)