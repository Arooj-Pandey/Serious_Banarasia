from pathlib import Path
import json
import logging
from langchain_openai import OpenAI
from translator.queryTranslator import Translator
from models.factory import ModelFactory
import os
from dotenv import load_dotenv
from utils.responseFormater import ResponseFormatter

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize models
model = ModelFactory.get_model("gemini", os.getenv("GEMINI_API_KEY"), "gemini-1.5-flash")

def generate_final_prompt(raw_results: dict, user_query: str) -> str:
    """Generate LLM-ready prompt with formatted search results"""
    try:
        # Format results for LLM consumption
        formatter = ResponseFormatter(raw_results, max_content_length=4000)
        formatted_results = formatter.format_for_llm()
        
        # Validate formatted results
        if not formatted_results.get('organic_results'):
            logger.warning("No organic results found in formatted data")
            
        # Load prompt template
        prompt_path = Path(__file__).parent.parent / "prompts" / "final_response" / "final_prompt.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt template not found at {prompt_path}")
            
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()

        # Create structured context
        context = {
            "query": user_query,
            "sources": [
                {
                    "domain": result["domain"],
                    "key_points": result["content"]["key_points"],
                    "main_content": result["content"]["main_content"][:3]  # First 3 paragraphs
                } 
                for result in formatted_results.get("organic_results", [])[:5]  # Top 5 results
            ],
            "related_questions": formatted_results.get("related_questions", [])[:3],
            "freshness": formatted_results.get("metadata", {}).get("processing_date")
        }

        # Generate final prompt
        llm_prompt = template.format(
            context=json.dumps(context, indent=2),
            query=user_query
        )

        logger.debug(f"Generated LLM prompt length: {len(llm_prompt)} characters")

        # Get model response with error handling
        response = model.generate_content(llm_prompt)
        return _parse_model_response(response)

    except Exception as e:
        logger.error(f"Prompt generation failed: {str(e)}")
        return f"Error processing request: {str(e)}"

def _parse_model_response(response) -> str:
    """Handle different model response formats uniformly"""
    try:
        if isinstance(response, dict):
            if 'choices' in response:
                return response['choices'][0]['text'].strip()
            if 'output' in response:
                return response['output'].strip()
                
        if hasattr(response, 'text'):
            return response.text.strip()
            
        if hasattr(response, 'content'):
            return response.content.strip()
            
        return str(response).strip()
        
    except Exception as e:
        logger.error(f"Response parsing failed: {str(e)}")
        return "Error processing model response"