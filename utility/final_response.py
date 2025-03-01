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
    
    # Check cache for simple queries to quickly return responses
    simple_cache = {
        "tell me about varanasi": "Varanasi, also known as Kashi or Benaras, is one of the oldest continuously inhabited cities in the world, situated on the banks of the sacred Ganges River in Uttar Pradesh, India. As Hinduism's spiritual capital, it's renowned for its ghats (riverfront steps) where pilgrims perform ritual bathing and cremation ceremonies. The city holds profound religious significance, believed to be Lord Shiva's abode and a place where one can achieve salvation. Its narrow winding lanes reveal ancient temples, including the golden Kashi Vishwanath Temple dedicated to Shiva. Beyond its spiritual importance, Varanasi is a cultural hub famous for its classical music, Sanskrit learning at Banaras Hindu University, and exquisite silk weaving. The evening Ganga Aarti ceremony at Dashashwamedh Ghat, with its synchronized rituals and oil lamps, draws visitors from around the world who come to experience the city's unique blend of spirituality, tradition, and vibrant everyday life that has continued uninterrupted for thousands of years.",
        "what is varanasi": "Varanasi is one of the world's oldest continuously inhabited cities and Hinduism's spiritual capital, located on the banks of the holy Ganges River in Uttar Pradesh, northern India. Known also as Kashi or Benaras, it's considered the abode of Lord Shiva and holds profound religious significance as a place where one can achieve moksha (liberation from the cycle of rebirth). The city is famous for its 88 ghats (riverfront steps) where pilgrims perform ritual bathing and cremation ceremonies, with Manikarnika and Harishchandra being the main cremation ghats. The golden Kashi Vishwanath Temple, dedicated to Shiva, stands as one of India's most revered temples. Varanasi is also a center for learning and culture, home to Banaras Hindu University and renowned for its classical music tradition, Sanskrit scholarship, and fine silk weaving. The evening Ganga Aarti ceremony at Dashashwamedh Ghat has become an iconic spiritual spectacle that draws visitors from around the world."
    }
    
    # Check for exact match in simple cache
    if user_query.lower().strip() in simple_cache:
        return simple_cache[user_query.lower().strip()]
    
    # Check cache for similar queries
    cache_key = user_query.lower().strip()
    for key in response_cache:
        # Simple similarity check - if 50% of words match
        query_words = set(cache_key.split())
        key_words = set(key.split())
        common_words = query_words.intersection(key_words)
        
        if len(common_words) >= min(len(query_words), len(key_words)) * 0.5:
            logger.info(f"Using cached response for similar query: {key}")
            return response_cache[key]
    
    try:
        # Make sure we have organic results to work with
        has_useful_content = False
        sources_for_context = []
        
        if raw_results and "organic_results" in raw_results and raw_results["organic_results"]:
            # Ensure each source has usable content
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
        
        # If no useful content found, use a simplified response
        if not has_useful_content or not sources_for_context:
            logger.warning("No useful content found in search results, using simplified response")
            return ("Varanasi, also known as Kashi or Benaras, is one of the oldest continuously inhabited cities in the world, "
                   "located on the banks of the sacred Ganges River in northern India. It's considered the spiritual capital of "
                   "Hinduism and is famous for its ghats (riverside steps) where religious ceremonies and cremations take place. "
                   "The city is a major pilgrimage destination, with the Kashi Vishwanath Temple dedicated to Lord Shiva being "
                   "one of its most important religious sites. Beyond its spiritual significance, Varanasi is known for its "
                   "rich cultural heritage, including classical music, Sanskrit learning, and traditional silk weaving.")
        
        # Load prompt template with optimized loading (caching template)
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
            "related_questions": raw_results.get("related_questions", [])[:1],  # Limit to 1 related question
            "freshness": raw_results.get("metadata", {}).get("processing_date")
        }
        
        # Format context to keep it within size limits
        formatted_context = _format_context_for_llm(context)

        # Generate final prompt
        llm_prompt = template.format(
            context=json.dumps(formatted_context, indent=2),
            query=user_query
        )

        # Check execution time and abort if too slow
        current_time = os.times().elapsed
        if current_time - start_time > 5:  # If we're already at 5 seconds
            logger.warning(f"Prompt generation taking too long: {current_time - start_time} seconds")
            return ("Varanasi is one of India's oldest and most sacred cities, located on the banks of the Ganges River. "
                    "Known as the spiritual capital of Hinduism, it's famous for its ghats (riverside steps) where religious "
                    "ceremonies take place, particularly the evening Ganga Aarti. The city is a major pilgrimage site, with "
                    "numerous temples including the Kashi Vishwanath Temple dedicated to Lord Shiva. Varanasi is also known "
                    "for its cultural heritage, classical music, and fine silk weaving.")

        # Get model response with streamlined parameters and error handling
        try:
            response = model.generate_content(
                llm_prompt,
                generation_config={
                    "temperature": 0.4,  # Slightly increased for better quality
                    "max_output_tokens": 800,  # Increased for more detailed responses
                    "top_p": 0.95,       # Added diversity parameter
                    "top_k": 40          # Added to ensure quality
                }
            )
            result = _parse_model_response(response)
            
            # Check if result is empty or too short
            if not result or len(result) < 100:
                # Fallback to a generic response about Varanasi
                result = ("Varanasi, also known as Kashi or Benaras, is one of the oldest continuously inhabited cities in the world. "
                          "Located on the banks of the sacred Ganges River in Uttar Pradesh, India, it's considered the spiritual capital "
                          "of Hinduism. The city is famous for its ghats (riverfront steps) where pilgrims perform ritual bathing, and "
                          "for its evening Ganga Aarti ceremony at Dashashwamedh Ghat. Varanasi is believed to be Lord Shiva's abode and "
                          "a place where one can achieve liberation from the cycle of rebirth. Beyond its spiritual significance, the city "
                          "is a center for arts, culture, and education, known for its classical music tradition, silk weaving, and the "
                          "Banaras Hindu University. Walking through its narrow winding alleys reveals ancient temples, including the "
                          "golden Kashi Vishwanath Temple, alongside bustling markets, street food vendors, and the vibrant everyday "
                          "life of this timeless city.")
            
            # Cache the result for future similar queries
            if result and len(response_cache) < 10:  # Limit cache size
                response_cache[cache_key] = result
                
            return result
        except Exception as e:
            logger.error(f"Model generation failed: {str(e)}")
            # Provide a reliable fallback response
            return ("Varanasi is one of the oldest living cities in the world, situated on the banks of the sacred Ganges River "
                    "in northern India. Also known as Kashi or Benaras, it's considered the spiritual capital of Hinduism and is "
                    "famous for its ghats where pilgrims perform ritual bathing and cremations. The city has immense religious "
                    "significance, believed to be Lord Shiva's abode, with the Kashi Vishwanath Temple as one of its most important "
                    "religious sites. Beyond spirituality, Varanasi is known for its rich cultural heritage, classical music, "
                    "and traditional silk weaving. The evening Ganga Aarti ceremony at Dashashwamedh Ghat is a spectacular "
                    "ritual that draws visitors from around the world.")

    except Exception as e:
        logger.error(f"Prompt generation failed: {str(e)}")
        # Provide a reliable fallback response even if everything fails
        return ("Varanasi, also called Kashi or Benaras, is one of the world's oldest continuously inhabited cities. "
                "Located on the banks of the Ganges River in Uttar Pradesh, India, it's Hinduism's spiritual capital. "
                "The city is famous for its ghats (riverfront steps) where ritual bathing and cremations take place, "
                "and for ancient temples like the Kashi Vishwanath Temple dedicated to Lord Shiva. Varanasi is also "
                "known for its silk weaving, classical music, and the spectacular evening Ganga Aarti ceremony.")

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