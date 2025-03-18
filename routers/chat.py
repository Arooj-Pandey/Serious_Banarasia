from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import time
import os
from pathlib import Path

# Import components from the existing chatbot
from models.factory import ModelFactory
from translator.queryTranslator import Translator as QueryTranslator
from keywords_Segregator.segregator import Segregator as KeywordsSegregator
from queryRouter.router import QueryRouter
from utils.responseFormater import ResponseFormatter
from utility.final_response import generate_final_prompt
from database.database import get_db
from database.models import Chat

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

router = APIRouter()

class ChatRequest(BaseModel):
    query: str = Field(..., description="The user's question or message to the chatbot")

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

# Create dependency for model initialization
def get_model():
    try:
        return ModelFactory.get_model("gemini", os.getenv("GEMINI_API_KEY"), "gemini-2.0-flash")
    except Exception as e:
        logger.error(f"Model initialization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI model initialization failed: {str(e)}")

def get_translator():
    try:
        return QueryTranslator(
            api_key=os.getenv("GEMINI_API_KEY"),
            model_type="gemini",
            model_name= "gemini-2.0-flash",
            prompt_template_path=str(Path(__file__).parent.parent / "prompts" / "translator" / "translator_prompt.txt")
        )
    except Exception as e:
        logger.error(f"Translator initialization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Query translator initialization failed: {str(e)}")

def get_segregator():
    try:
        return KeywordsSegregator(
            api_key=os.getenv("GEMINI_API_KEY"),
            model_type="gemini",
            model_name= "gemini-2.0-flash",
            prompt_template_path=str(Path(__file__).parent.parent / "prompts" / "query_router" / "query_keywords_seggregator.txt")
        )
    except Exception as e:
        logger.error(f"Segregator initialization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Keywords segregator initialization failed: {str(e)}")

@router.post("/chat", response_model=ChatResponse)
async def process_chat(
    request: Request,
    chat_request: ChatRequest,
    model=Depends(get_model),
    translator=Depends(get_translator),
    segregator=Depends(get_segregator),
    db: Session = Depends(get_db)
):
    start_time = time.time()
    
    try:
        user_query = chat_request.query
        client_ip = request.client.host
        logger.info(f"Processing query from IP {client_ip}: {user_query}")
        
        # Query processing logic
        if len(user_query.split()) <= 8 and any(keyword in user_query.lower() for keyword in ["varanasi", "banaras", "kashi"]):
            restructured_query = user_query
            logger.info("Simple query detected, skipping translation")
        else:
            logger.info("Step 1: Starting query translation")
            restructured_query = translator.translate_query(user_query)
            logger.info(f"Step 1 complete: Query translated successfully")
        
        ai_response = "Default response if processing fails"
        try:
            # Generate response
            keywords = segregator.keywords_seggregator(restructured_query)
            router = QueryRouter(serper_api_key=os.getenv("SERPER_API_KEY"))
            raw_results = router.route_keywords(keywords)
            formatter = ResponseFormatter(raw_results, max_content_length=2000)
            formatted_results = formatter.format_for_llm()
            ai_response = generate_final_prompt(formatted_results, user_query)
            
            # Store chat interaction
            chat_record = Chat(
                user_ip=client_ip,
                input_text=user_query,
                output_text=ai_response
            )
            db.add(chat_record)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            ai_response = "I apologize, but I encountered an error processing your question. Please try again."
            
            # Store error interaction
            chat_record = Chat(
                user_ip=client_ip,
                input_text=user_query,
                output_text=ai_response
            )
            db.add(chat_record)
            db.commit()
        
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
        
        # Store error interaction
        chat_record = Chat(
            user_ip=client_ip,
            input_text=chat_request.query,
            output_text=error_message
        )
        db.add(chat_record)
        db.commit()
        
        return ChatResponse(
            response=error_message,
            sources=[],
            images=[],
            processing_time=processing_time
        )