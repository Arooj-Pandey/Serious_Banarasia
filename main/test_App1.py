import json
import os
import logging
import streamlit as st
from pathlib import Path
from typing import Dict, List
import sys
sys.path.append(os.path.abspath("D:/projects/Serious_Banarasia"))
from translator.Query_Restructure_and_Segregation import QueryRestructurer
from query_router.keywords_router_and_API_Result_Parser import get_keywords_result_dict, route_keywords, parse_api_results
from main.final_response import generate_final_prompt
from models.gemini import GeminiModel



# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Gemini Model
gemini_api_key = os.getenv("Genai_api")
if not gemini_api_key:
    raise ValueError("Genai_api environment variable not set")
GM = GeminiModel(gemini_api = gemini_api_key, model_name="gemini-1.5-flash")

# def route_keywords(keywords: Dict[str, List[str]]) -> Dict[str, List[Dict]]:
#     results = {"text_api": [], "image_api": []}
#     categories_to_process = {k: v for k, v in keywords.items() if k != 'api_needed'}
    
#     for category, keyword_list in categories_to_process.items():
#         if category not in results:
#             logger.warning(f"Unknown category {category} encountered")
#             continue
            
#         for keyword in keyword_list:
#             try:
#                 result = serperquery(keyword) if category == "text_api" else serper_img_query(keyword)
#                 if isinstance(result, str):
#                     result = json.loads(result)
#                 results[category].append({keyword: result})
#             except json.JSONDecodeError as je:
#                 logger.error(f"JSON decode error for {keyword}: {str(je)}")
#             except Exception as e:
#                 logger.error(f"Error processing {keyword} for {category}: {str(e)}")
    
#     try:
#         with open("keywords_result_dict.json", "w", encoding='utf-8') as f:
#             json.dump(results, f, indent=4, ensure_ascii=False)
#         logger.info("Results successfully saved to keywords_result_dict.json")
#     except Exception as e:
#         logger.error(f"Error saving results to JSON: {str(e)}")
    
#     return results

# def parse_api_results(json_data: Dict) -> Dict:
#     parsed_results = {}
    
#     for api_type, responses in json_data.items():
#         parsed_results[api_type] = []
        
#         for response in responses:
#             try:
#                 query = next(iter(response))
#                 results = response[query]
                
#                 cleaned_results = []
#                 if 'organic' in results:
#                     cleaned_results = [
#                         {
#                             'title': result.get('title', ''),
#                             'link': result.get('link', ''),
#                             'snippet': result.get('snippet', '')
#                         }
#                         for result in results['organic']
#                     ]
#                 elif 'images' in results:
#                     cleaned_results = [
#                         {
#                             'title': result.get('title', ''),
#                             'imageUrl': result.get('imageUrl', '')
#                         }
#                         for result in results['images']
#                     ]
                
#                 parsed_results[api_type].append({'results': cleaned_results})
                        
#             except Exception as e:
#                 logger.error(f"Error parsing response in {api_type}: {str(e)}")
#                 continue
    
#     return parsed_results

# def generate_final_prompt(results: Dict, user_query: str) -> str:
#     prompt_path = Path(__file__).parent.parent / "prompts" / "final_response" / "final_prompt.txt"
#     if not prompt_path.is_file():
#         raise FileNotFoundError(f"Prompt file not found at {prompt_path}")

#     with open(prompt_path, "r", encoding="utf-8") as f:
#         template = f.read()
#         formatted_prompt = template.format(results=results, query=user_query)

#     return GM.generate_content(formatted_prompt)

def main():
    QR = QueryRestructurer(gemini_api_key, "gemini-1.5-flash", Path(__file__).parent.parent / "prompts" / "translator"/ "translator_prompt.txt")
    st.title("Multi-Source Query Assistant")
    st.write("Get comprehensive information from multiple sources!")

    query = st.text_input("Enter your query:", placeholder="What would you like to know?")
    
    if st.button("Search and Analyze") or query:
        if not query:
            st.warning("Please enter a query.")
            return
        
        try:
            with st.spinner("Processing your query..."):
                restructured_query = QR.restructure_query(query)  #restructures the query
                keywords = get_keywords_result_dict(restructured_query) #get keywords from the restructured query
                results = route_keywords(keywords) 
                
                with open('keywords_result_dict.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    results = parse_api_results(data)

                final_prompt = generate_final_prompt(results, query)
                
                st.subheader("AI-Generated Summary")
                st.write(final_prompt)
                
                if "image_api" in results:
                    st.subheader("Image Results")
                    for image_result in results["image_api"]:
                        for item in image_result.get("results", []):
                            if item.get("imageUrl"):
                                st.image(item["imageUrl"], caption=item.get("title", ""))
                
        except Exception as e:
            logger.error(f"Error in main: {str(e)}")
            st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
