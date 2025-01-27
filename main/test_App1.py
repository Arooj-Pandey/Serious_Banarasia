import json
import os
import logging
import streamlit as st  # <-- Streamlit import must stay at top
from pathlib import Path
import sys
import time

# 1. SET PAGE CONFIG FIRST
st.set_page_config(
    page_title="Varanasi AI Guide", 
    page_icon="🌐", 
    layout="centered"
)

# 2. THEN SET OTHER IMPORTS
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)
sys.path.append(os.path.abspath(r"D:\Projects\Serious_Banarasia"))

# Rest of imports
from translator.queryTranslator import Translator
from queryRouter.router import QueryRouter
from main.final_response import generate_final_prompt
from models.factory import ModelFactory
from keywords_Segregator.segregator import Segregator
from utils.responseFormater import ResponseFormatter

# 3. THEN SET OTHER CONFIGURATIONS
# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Gemini Model
model = ModelFactory.get_model("gemini", os.getenv("gemini_api"), "gemini-1.5-flash")

# Custom CSS for Perplexity-like interface


def display_conversation(history):
    """Display chat history with animated messages"""
    for entry in history:
        if entry["type"] == "user":
            st.markdown(f'<div class="user-message">🙋♂️ {entry["content"]}</div>', unsafe_allow_html=True)
        else:
            with st.container():
                st.markdown(f'<div class="ai-message">🤖 {entry["content"]}</div>', unsafe_allow_html=True)
                
                # Display sources if available
                if "sources" in entry:
                    with st.expander("📚 Sources", expanded=True):
                        for source in entry["sources"]:
                            st.markdown(f"""
                            <div class="source-card">
                                <a href="{source['link']}" target="_blank" style="text-decoration:none; color:#2b5876;">
                                    <b>🌐 {source['domain']}</b>
                                </a>
                                <p style="margin:0.5rem 0; color:#666;">{source['snippet']}</p>
                            </div>
                            """, unsafe_allow_html=True)
                
                # Display images if available
                if "images" in entry:
                    with st.expander("🖼️ Related Images", expanded=True):
                        cols = st.columns(3)
                        for idx, img in enumerate(entry["images"][:6]):
                            with cols[idx%3]:
                                st.image(img["url"], caption=img.get("title", ""), use_column_width=True)

def main():
    
    st.markdown("""
<style>
    /* Main container styling */
    .main {
        max-width: 800px;
        margin: 0 auto;
        padding: 1rem;
    }
    
    /* Chat message styling */
    .user-message {
        background-color: #f0f2f6;
        border-radius: 15px;
        padding: 1rem;
        margin: 0.5rem 0;
        max-width: 80%;
        float: right;
        clear: both;
    }
    
    .ai-message {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        max-width: 80%;
        float: left;
        clear: both;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Source citations */
    .source-card {
        border-left: 3px solid #4a90e2;
        padding: 0.5rem 1rem;
        margin: 0.5rem 0;
        background-color: #f8f9fa;
        border-radius: 4px;
    }
    
    /* Image grid styling */
    .image-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
    
    /* Input bar styling */
    .stTextInput>div>div>input {
        border-radius: 25px;
        padding: 1rem 1.5rem;
        font-size: 1rem;
    }
    
    /* Typing animation */
    @keyframes typing {
        from { width: 0 }
        to { width: 100% }
    }
    
    .typing-indicator {
        display: inline-block;
        overflow: hidden;
        border-right: 2px solid #666;
        white-space: nowrap;
        margin: 0 auto;
        letter-spacing: 2px;
        animation: typing 1s steps(40, end), blink-caret 0.75s step-end infinite;
    }
</style>
""", unsafe_allow_html=True)
    
    
    # Initialize session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Header
    st.markdown("<h1 style='text-align: center; margin-bottom: 2rem; color: #2b5876;'>Varanasi AI Guide</h1>", unsafe_allow_html=True)
    
    # Chat container
    chat_container = st.container()
    with chat_container:
        display_conversation(st.session_state.chat_history)
    
    # Input at bottom
    with st.form(key='chat_form', clear_on_submit=True):
        col1, col2 = st.columns([6, 1])
        with col1:
            user_input = st.text_input(
                "Ask me anything about Varanasi:",
                placeholder="What are the best places to visit in Varanasi?",
                label_visibility="collapsed"
            )
        with col2:
            submit_button = st.form_submit_button("🚀")
    
    if submit_button and user_input:
        st.session_state.chat_history.append({"type": "user", "content": user_input})
        
        with st.spinner("🔍 Researching your query..."):
            try:
                # Initialize components
                tslr = Translator(os.getenv("GEMINI_API_KEY"), "gemini", "gemini-1.5-flash")
                sgr = Segregator(
                    os.getenv("GEMINI_API_KEY"), 
                    "gemini", 
                    "gemini-1.5-flash",
                    Path(__file__).parent.parent / "prompts" / "query_router" / "query_keywords_seggregator.txt"
                )
                
                # Process query
                restructured_query = tslr.translate_query(user_input)
                keywords = sgr.keywords_seggregator(restructured_query)
                
                # Route keywords and format results
                router = QueryRouter(serper_api_key=os.getenv("SERPER_API_KEY"))
                raw_results = router.route_keywords(keywords)
                
                # Format for LLM
                formatter = ResponseFormatter(raw_results)
                formatted_results = formatter.format_for_llm()
                
                # Generate final response
                ai_response = generate_final_prompt(formatted_results, user_input)
                
                # Add to chat history
                response_entry = {
                    "type": "ai",
                    "content": ai_response,
                    "sources": formatted_results.get("organic_results", [])[:3],
                    "images": formatted_results.get("image_results", [])[:6]
                }
                
                st.session_state.chat_history.append(response_entry)
                st.rerun()
                
            except Exception as e:
                logger.error(f"Error processing query: {str(e)}")
                st.error(f"An error occurred: {str(e)}")
                st.session_state.chat_history.append({
                    "type": "ai",
                    "content": f"Sorry, I encountered an error: {str(e)}"
                })
                st.rerun()

if __name__ == "__main__":
    main()