from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import os
from dotenv import load_dotenv

import streamlit as st
from tools.serper import SerperClient
from models.gemini import GeminiModel

# Load environment variables
load_dotenv()

# Constants
TEMPLATE_PATH = Path(__file__).parent.parent / "prompts" / "query_router" / "query_keywords_seggregator.txt"
RESULTS_FILE = Path(__file__).parent.parent / "keywords_result_dict.json"

# Initialize clients
serper_client = SerperClient(api_key=os.getenv("SERPER_API"))
gemini_model = GeminiModel(
    api_key=os.getenv("GENAI_API"), 
    model_name="gemini-1.5-flash"
)

def get_keywords_result_dict(query: str) -> Dict[str, Any]:
    """Extract keywords from user query using template."""
    try:
        if not TEMPLATE_PATH.is_file():
            raise FileNotFoundError(f"Template not found: {TEMPLATE_PATH}")
            
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        formatted_template = template.format(re_structured_query=query)
        
        keywords_result = gemini_model.generate_content(formatted_template)
        
        # Extract JSON content
        start_index = keywords_result.find("{")
        end_index = keywords_result.rfind("}") + 1
        json_content = keywords_result[start_index:end_index]
        
        return json.loads(json_content)
        
    except json.JSONDecodeError as e:
        return {"error": "JSONDecodeError", "message": str(e), "content": keywords_result}
    except Exception as e:
        return {"error": "Exception", "message": str(e), "content": keywords_result}

def route_keywords(keywords: Dict[str, List[str]]) -> Dict[str, List[Dict]]:
    """Route keywords to appropriate search APIs."""
    results = {"text_api": [], "image_api": []}
    
    # Filter out control parameters
    categories = {k: v for k, v in keywords.items() if k != 'api_needed'}
    
    for category, keyword_list in categories.items():
        if category not in results:
            st.warning(f"Unknown category: {category}")
            continue
            
        for keyword in keyword_list:
            try:
                # Route to appropriate API
                if category == "text_api":
                    result = serper_client.search_query(keyword)
                elif category == "image_api":
                    result = serper_client.image_query(keyword)
                else:
                    continue
                
                # Parse response
                if isinstance(result, str):
                    result = json.loads(result)
                results[category].append({keyword: result})
                    
            except Exception as e:
                st.error(f"Error processing {keyword}: {str(e)}")
                continue

    # Save results
    try:
        RESULTS_FILE.write_text(
            json.dumps(results, indent=4, ensure_ascii=False),
            encoding='utf-8'
        )
    except Exception as e:
        st.error(f"Error saving results: {str(e)}")
        
    return results

def parse_api_results(json_data: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
    """Parse and clean API results."""
    parsed_results: Dict[str, List[Dict]] = {}
    
    try:
        for api_type, responses in json_data.items():
            parsed_results[api_type] = []
            
            for response in responses:
                try:
                    query = next(iter(response))
                    results = response[query]
                    cleaned_results = []

                    if 'organic' in results:
                        # Handle text search results
                        for result in results['organic']:
                            cleaned_results.append({
                                'title': result.get('title', ''),
                                'link': result.get('link', ''),
                                'snippet': result.get('snippet', '')
                            })
                    elif 'images' in results:
                        # Handle image search results
                        for result in results['images']:
                            cleaned_results.append({
                                'title': result.get('title', ''),
                                'imageUrl': result.get('imageUrl', '')
                            })
                            
                    if cleaned_results:
                        parsed_results[api_type].append({'results': cleaned_results})
                        
                except Exception as e:
                    st.error(f"Error parsing {api_type} response: {str(e)}")
                    continue
                    
    except Exception as e:
        st.error(f"Error parsing results: {str(e)}")
        return {}
        
    return parsed_results