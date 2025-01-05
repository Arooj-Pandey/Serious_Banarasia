from dotenv import load_dotenv
import os
import google.generativeai as genai
from .base import BaseModel

load_dotenv()

class GeminiModel(BaseModel):
    def __init__(self, gemini_api: str, model_name: str):
        gemini_api = os.getenv("Genai_api", gemini_api)
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
        
        self.model = genai.GenerativeModel(model_name = model_name, generation_config=self.generation_config, safety_settings=self.safety_settings)

    def generate_content(self, prompt: str) -> str:
        
        response = self.model.generate_content([prompt])
        
        return response.text
