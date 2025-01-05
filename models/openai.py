from dotenv import load_dotenv
from .base import BaseModel
from openai import OpenAI 

load_dotenv()

class ModelOpenAI(BaseModel):
    
    def __init__(self, model_name: str, api_key: str = None):
        self.model_name = model_name
        self.client = OpenAI(api_key = api_key)
    
    def generate_content(self, prompt: str) -> str:
        
        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "developer", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        return completion.choices[0].message.content
