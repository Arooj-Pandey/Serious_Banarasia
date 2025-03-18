from dotenv import load_dotenv
import os
import google.generativeai as genai
from .base import BaseModel
from .openai import ModelOpenAI

load_dotenv()

class GeminiModel(BaseModel):
    def __init__(self, gemini_api: str, model_name: str):
        gemini_api = os.getenv("GEMINI_API_KEY", gemini_api)
        self.openai_fallback = None
        
        try:
            genai.configure(api_key=gemini_api)
            
            self.generation_config = {
                "temperature": 1,
                "top_p": 1,
                "top_k": 1,
                "max_output_tokens": 30720,
            }
            self.safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
            ]
            
            self.model = genai.GenerativeModel(model_name=model_name, 
                                             generation_config=self.generation_config, 
                                             safety_settings=self.safety_settings)
        except Exception as e:
            # If Gemini initialization fails, prepare OpenAI fallback
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise Exception("Gemini API unavailable and no OpenAI API key found")
            self.openai_fallback = ModelOpenAI("gpt-3.5-turbo", openai_api_key)

    def generate_content(self, prompt: str) -> str:
        try:
            # Try Gemini first if available
            if not self.openai_fallback:
                response = self.model.generate_content(prompt)
                return response.text
            # Use OpenAI fallback if Gemini failed to initialize
            else:
                return self.openai_fallback.generate_content(prompt)
        except Exception as e:
            if "User location is not supported" in str(e) and not self.openai_fallback:
                # Initialize OpenAI fallback on location error
                openai_api_key = os.getenv("OPENAI_API_KEY")
                if not openai_api_key:
                    raise Exception("Gemini API unavailable and no OpenAI API key found")
                self.openai_fallback = ModelOpenAI("gpt-3.5-turbo", openai_api_key)
                return self.openai_fallback.generate_content(prompt)
            raise Exception(f"Failed to generate content: {str(e)}")
