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
from main.final_response import generate_final_prompt

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

# Add CORS middleware with settings that match frontend development needs
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    model=Depends(get_model),
    translator=Depends(get_translator),
    segregator=Depends(get_segregator)
):
    """
    Process a chat query and return a response with sources and images.
    
    - **query**: The user's question about Varanasi
    - **user_id**: Optional unique identifier for the user
    
    Returns a response with the AI-generated answer, relevant sources, and images.
    """
    start_time = time.time()
    
    try:
        user_query = request.query
        logger.info(f"Processing query: {user_query}")
        
        # Process query using the existing pipeline
        restructured_query = translator.translate_query(user_query)
        keywords = segregator.keywords_seggregator(restructured_query)
        
        # Route keywords and format results
        router = QueryRouter(serper_api_key=os.getenv("SERPER_API_KEY"))
        raw_results = router.route_keywords(keywords)
        
        # Format for LLM
        formatter = ResponseFormatter(raw_results)
        formatted_results = formatter.format_for_llm()
        
        # Generate final response
        ai_response = generate_final_prompt(formatted_results, user_query)
        
        # Format sources according to the Source model
        sources = []
        if formatted_results.get("organic_results"):
            for result in formatted_results["organic_results"][:3]:
                snippet = result.get("snippet", "")
                if not snippet and result.get("main_content"):
                    snippet = result["main_content"][0] if isinstance(result["main_content"], list) else str(result["main_content"])
                
                source = Source(
                    domain=result.get("domain", "unknown"),
                    link=result.get("link", ""),
                    snippet=snippet
                )
                sources.append(source)
        
        # Format images according to the Image model
        images = []
        if formatted_results.get("image_results"):
            for image in formatted_results["image_results"][:4]:
                image_obj = Image(
                    url=image.get("url", ""),
                    title=image.get("title")
                )
                images.append(image_obj)
        
        # Calculate processing time and return formatted response
        processing_time = time.time() - start_time
        return ChatResponse(
            response=ai_response if ai_response else "I apologize, but I couldn't generate a response for your query.",
            sources=sources,
            images=images,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.exception(f"Error processing chat: {str(e)}")
        processing_time = time.time() - start_time
        return ChatResponse(
            response="I'm sorry, I encountered an error while processing your question. Please try again or ask something different.",
            sources=[],
            images=[],
            processing_time=processing_time
        )

# Make sure the app is directly accessible as a module attribute
__all__ = ['app']

if __name__ == "__main__":
    import uvicorn
    
    # Use port 8080 as configured
    port = int(os.getenv("PORT", 8080))
    
    # Use the app instance directly rather than an import string
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=False  # Disable reload when running directly with the app instance
    )