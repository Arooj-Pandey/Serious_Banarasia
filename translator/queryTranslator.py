from pathlib import Path
import os
from models.factory import ModelFactory
from dotenv import load_dotenv
load_dotenv()

class Translator:
    def __init__(self, api_key: str, model_type: str, model_name: str, prompt_template_path: str = None):
        self.api_key = api_key
        self.model_name = model_name
        self.model_type = model_type
        if prompt_template_path:
            self.prompt_template_path = Path(prompt_template_path)
        else:
            self.prompt_template_path = Path("prompts/translator/translator_prompt.txt")
            
        self.model = ModelFactory.get_model(model_type, api_key, model_name)
        
    def load_prompt_template(self) -> str:
        try:
            with open(self.prompt_template_path,"r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt template not found at {self.prompt_template_path}")
        except Exception as e:
            raise Exception(f"Error loading prompt template: {str(e)}")
    
    def translate_query(self, query: str) -> str:
        try:
            template = self.load_prompt_template()
            
            formatted_prompt = template.format(user_query=query)
            
            return self.model.generate_content(formatted_prompt)
        
        except Exception as e:
            print(f"Error restructuring query: {str(e)}")
            return None
