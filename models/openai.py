import getpass
import os
from dotenv import load_dotenv
load_dotenv()
import requests



class OpenAI:
    def __init__(self, model, api_key = None):
        self.model = model
        self.temperature = 0
        self.max_retries = 2
        self.api_key = os.getenv("open_ai")
        self.base_url = "https://api.openai.com/v1/engines"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        
    def invoke(self, prompt):
        url = f"{self.base_url}/{self.model}/completions"
        data = {
            "prompt": prompt,
            "max_tokens": 1024,
            "temperature": self.temperature,
        }
        response = requests.post(url, headers=self.headers, json=data)
        return response.json()
