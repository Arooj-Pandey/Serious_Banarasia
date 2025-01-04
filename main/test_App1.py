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
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Gemini Model
gemini_api_key = os.getenv("Genai_api")
if not gemini_api_key:
    raise ValueError("Genai_api environment variable not set")
GM = GeminiModel(gemini_api=gemini_api_key, model_name="gemini-1.5-flash")

def format_results_for_display(results: Dict) -> Dict:
    """Format results to be visually appealing."""
    formatted_results = {}
    for key, value in results.items():
        if isinstance(value, list):
            formatted_results[key] = "\n".join([f"- {item}" for item in value])
        elif isinstance(value, dict):
            formatted_results[key] = "\n".join([f"{sub_key}: {sub_value}" for sub_key, sub_value in value.items()])
        else:
            formatted_results[key] = str(value)
    return formatted_results

def main():
    # Configure the Streamlit UI
    st.set_page_config(page_title="Varanasi AI Guide", page_icon="🌐", layout="wide")
    
    # Page Header
    st.markdown(
        """
        <style>
        .main-header {
            font-size: 2.5em;
            color: #6b2737;
            text-align: center;
            font-family: 'Georgia', serif;
            background-color: #f4e3d7;
            padding: 10px;
            border-radius: 10px;
        }
        .query-input {
            margin-top: 20px;
            font-size: 1.2em;
            color: #333;
        }
        .section-header {
            font-size: 1.8em;
            color: #7b3f61;
            margin-bottom: 10px;
        }
        </style>
        <div class="main-header">Varanasi AI Chatbot - Your Personalized Guide</div>
        """,
        unsafe_allow_html=True
    )

    # Initialize Query Restructurer
    QR = QueryRestructurer(
        gemini_api_key, 
        "gemini-1.5-flash", 
        Path(__file__).parent.parent / "prompts" / "translator" / "translator_prompt.txt"
    )

    # Input Section
    query = st.text_input(
        "Enter your query about Varanasi:", 
        placeholder="E.g., What are the top places to visit in Varanasi?", 
        key="query_input"
    )

    if st.button("Search and Analyze") or query:
        if not query:
            st.warning("Please enter a query.")
            return

        try:
            with st.spinner("Processing your query..."):
                # Query restructuring and processing
                summary_header = st.empty()
                summary_container = st.empty()
                image_header = st.empty()
                image_container = st.empty()
                
                restructured_query = QR.restructure_query(query)
                keywords = get_keywords_result_dict(restructured_query)
                results = route_keywords(keywords)

                with open('keywords_result_dict.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    results = parse_api_results(data)

                formatted_results = format_results_for_display(results)
                
                summary_header.markdown("""<div class='section-header'>AI-Generated Summary</div>""", unsafe_allow_html=True)
                 
                if isinstance(results, dict) and 'choices' in results:
                    final_text = results['choices'][0]['text'].strip()
                else:
                    final_text = generate_final_prompt(results, query)

                # Display Results
                # st.markdown("""<div class='section-header'>AI-Generated Summary</div>""", unsafe_allow_html=True)
                # st.markdown(f"<p style='font-size: 1.1em;'>{final_prompt}</p>", unsafe_allow_html=True)

                displayed_text = ""
                
                for char in final_text:
                    displayed_text += char
                    summary_container.markdown(
                        f"<p style='font-size: 1.1em;'>{displayed_text}▌</p>", 
                        unsafe_allow_html=True
                    )
                    time.sleep(0.01)

                summary_container.markdown(
                    f"<p style='font-size: 1.1em;'>{displayed_text}</p>", 
                    unsafe_allow_html=True
                )
                
                if "image_api" in results:
                    image_header.markdown("""<div class='section-header'>Image Results</div>""", unsafe_allow_html=True)
                    image_results = results["image_api"]
                    cols = st.columns(3)
                    with image_container:# Display images in a grid format
                        for idx, image_result in enumerate(image_results):
                            for item in image_result.get("results", []):
                                if item.get("imageUrl"):
                                    with cols[idx % 3]:
                                        st.image(
                                            item["imageUrl"], 
                                            # caption=item.get("title", ""), 
                                            use_container_width=True
                                        )
                
        except Exception as e:
            logger.error(f"Error in main: {str(e)}")
            st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
