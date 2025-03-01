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
        # Define a timeout threshold - adjusted for faster response
        MAX_PROCESSING_TIME = 12  # seconds - reduced from 25 to 12
        
        user_query = request.query
        logger.info(f"Processing query: {user_query}")
        
        # Skip translation for simple queries (optimization)
        if len(user_query.split()) <= 8 and any(keyword in user_query.lower() for keyword in ["varanasi", "banaras", "kashi"]):
            restructured_query = user_query
            logger.info("Simple query detected, skipping translation")
        else:
            # Log each step to help diagnose which part might be causing timeout
            logger.info("Step 1: Starting query translation")
            restructured_query = translator.translate_query(user_query)
            logger.info(f"Step 1 complete: Query translated successfully")
        
        # Check elapsed time after each major operation
        current_time = time.time()
        if current_time - start_time > MAX_PROCESSING_TIME * 0.3:  # 30% of max time
            logger.warning(f"Translation taking too long: {current_time - start_time} seconds")
            return ChatResponse(
                response="I apologize, but processing your query is taking longer than expected. Please try a simpler question.",
                sources=[],
                images=[],
                processing_time=current_time - start_time
            )
        
        logger.info("Step 2: Starting keywords segregation")
        keywords = segregator.keywords_seggregator(restructured_query)
        logger.info(f"Step 2 complete: Keywords extracted: {keywords}")
        
        # Limit the number of keywords processed
        if "search_api" in keywords and len(keywords["search_api"]) > 2:
            keywords["search_api"] = keywords["search_api"][:2]  # Limit to top 2 search keywords
            
        if "image_api" in keywords and len(keywords["image_api"]) > 1:
            keywords["image_api"] = keywords["image_api"][:1]  # Limit to top 1 image keyword
        
        # Check elapsed time
        current_time = time.time()
        if current_time - start_time > MAX_PROCESSING_TIME * 0.5:  # 50% of max time
            logger.warning(f"Keywords extraction taking too long: {current_time - start_time} seconds")
            return ChatResponse(
                response="I'm processing your complex query, but it's taking longer than expected. Please try again with a more focused question.",
                sources=[],
                images=[],
                processing_time=current_time - start_time
            )
        
        # Route keywords and format results
        logger.info("Step 3: Starting query routing")
        router = QueryRouter(serper_api_key=os.getenv("SERPER_API_KEY"))
        raw_results = router.route_keywords(keywords)
        logger.info(f"Step 3 complete: Query routing complete")
        
        # Check elapsed time
        current_time = time.time()
        if current_time - start_time > MAX_PROCESSING_TIME * 0.7:  # 70% of max time
            logger.warning(f"Query routing taking too long: {current_time - start_time} seconds")
            # If we have results but running out of time, use a simplified approach
            simple_response = "Based on your query, I found some information but couldn't complete full processing in time. Here's what I can tell you: "
            if raw_results and isinstance(raw_results, dict) and raw_results.get('organic'):
                first_result = raw_results['organic'][0] if raw_results['organic'] else {}
                simple_response += first_result.get('snippet', 'Please try again with a simpler question.')
            
            return ChatResponse(
                response=simple_response,
                sources=[],
                images=[],
                processing_time=current_time - start_time
            )
        
        # Format for LLM
        logger.info("Step 4: Formatting response for LLM")
        formatter = ResponseFormatter(raw_results, max_content_length=2000)  # Reduced from default 4000
        formatted_results = formatter.format_for_llm()
        logger.info(f"Step 4 complete: Response formatted for LLM")
        
        # Generate final response
        logger.info("Step 5: Generating final response")
        ai_response = generate_final_prompt(formatted_results, user_query)
        logger.info(f"Step 5 complete: Final response generated")
        
        # Format sources according to the Source model - limit to top 2 sources
        sources = []
        if formatted_results.get("organic_results"):
            for result in formatted_results["organic_results"][:2]:  # Reduced from 3 to 2
                snippet = result.get("snippet", "")
                if not snippet and result.get("main_content"):
                    snippet = result["main_content"][0] if isinstance(result["main_content"], list) else str(result["main_content"])
                
                source = Source(
                    domain=result.get("domain", "unknown"),
                    link=result.get("link", ""),
                    snippet=snippet[:150]  # Limit snippet length to 150 chars
                )
                sources.append(source)
        
        # Format images according to the Image model - limit to top 2 images
        images = []
        if formatted_results.get("image_results"):
            for image in formatted_results["image_results"][:2]:  # Reduced from 4 to 2
                image_obj = Image(
                    url=image.get("url", ""),
                    title=image.get("title")
                )
                images.append(image_obj)
        
        # Calculate processing time and return formatted response
        processing_time = time.time() - start_time
        logger.info(f"Total processing time: {processing_time} seconds")
        return ChatResponse(
            response=ai_response if ai_response else "I apologize, but I couldn't generate a response for your query.",
            sources=sources,
            images=images,
            processing_time=processing_time
        )
        
    except Exception as e:
        # Enhanced error logging
        logger.exception(f"Error processing chat: {str(e)}")
        processing_time = time.time() - start_time
        logger.error(f"Failed after {processing_time} seconds")
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)