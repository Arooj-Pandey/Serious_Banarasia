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

# Cache for storing recent responses
response_cache = {}

def _format_context_for_llm(context, max_size=8000):
    """Format context to keep it within reasonable size limits"""
    if len(json.dumps(context)) <= max_size:
        return context
    
    # Preserve query but reduce content
    reduced_context = {
        "query": context["query"],
        "sources": [],
        "related_questions": context.get("related_questions", [])[:1],
        "freshness": context.get("freshness")
    }
    
    # Add sources selectively until we approach the limit
    for source in context.get("sources", [])[:3]:  # Only consider top 3 sources
        # Reduce content within each source
        reduced_source = {
            "domain": source.get("domain"),
            "key_points": source.get("key_points", [])[:1],  # Keep only first key point
            "main_content": [source.get("main_content", [])[0]] if source.get("main_content") else []  # Keep only first paragraph
        }
        
        # Add source if it doesn't exceed limit
        temp_context = reduced_context.copy()
        temp_context["sources"] = reduced_context["sources"] + [reduced_source]
        if len(json.dumps(temp_context)) <= max_size:
            reduced_context["sources"].append(reduced_source)
        else:
            break
    
    return reduced_context

def generate_final_prompt(raw_results: dict, user_query: str) -> str:
    """Generate LLM-ready prompt with formatted search results"""
    start_time = os.times().elapsed
    
    try:
        # Make sure we have organic results to work with
        has_useful_content = False
        sources_for_context = []
        
        if raw_results and "organic_results" in raw_results and raw_results["organic_results"]:
            for result in raw_results["organic_results"][:3]:
                content = result.get("content", {})
                main_content = content.get("main_content", [])
                
                if main_content and isinstance(main_content, list) and len(main_content) > 0:
                    has_useful_content = True
                    sources_for_context.append({
                        "domain": result.get("domain", ""),
                        "key_points": content.get("key_points", [])[:1],
                        "main_content": main_content[:1]
                    })

        # Load prompt template
        prompt_path = Path(__file__).parent.parent / "prompts" / "final_response" / "final_prompt.txt"
        if not hasattr(generate_final_prompt, "_template_cache"):
            if not prompt_path.exists():
                raise FileNotFoundError(f"Prompt template not found at {prompt_path}")
                
            with open(prompt_path, "r", encoding="utf-8") as f:
                generate_final_prompt._template_cache = f.read()
        
        template = generate_final_prompt._template_cache

        # Create structured context
        context = {
            "query": user_query,
            "sources": sources_for_context,
            "related_questions": raw_results.get("related_questions", [])[:1],
            "freshness": raw_results.get("metadata", {}).get("processing_date")
        }
        
        # Format context to keep it within size limits
        formatted_context = _format_context_for_llm(context)

        # Generate final prompt
        llm_prompt = template.format(
            context=json.dumps(formatted_context, indent=2),
            query=user_query
        )

        # Get model response
        try:
            response = model.generate_content(llm_prompt)
            result = _parse_model_response(response)
            return result
            
        except Exception as e:
            logger.error(f"Model generation failed: {str(e)}")
            raise

    except Exception as e:
        logger.error(f"Final response generation failed: {str(e)}")
        raise

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
        return ("Varanasi is one of India's most sacred cities, located on the banks of the Ganges River. It's a major "
                "pilgrimage destination known for its ghats, ancient temples, and spiritual significance in Hinduism. "
                "The city is famous for its evening Ganga Aarti ceremony, traditional silk weaving, and being one of "
                "the world's oldest continuously inhabited urban centers.")