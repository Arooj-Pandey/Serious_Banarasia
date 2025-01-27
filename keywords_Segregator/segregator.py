from pathlib import Path
import os
from models.factory import ModelFactory
from dotenv import load_dotenv
import ast
load_dotenv()
import json

class Segregator:
    def __init__(self, api_key: str, model_type: str, model_name: str, prompt_template_path: str = None):
        self.api_key = api_key
        self.model_name = model_name
        self.model_type = model_type
        if prompt_template_path:
            self.prompt_template_path = Path(prompt_template_path)
        else:
            self.prompt_template_path = Path("prompts/query_router/query_keywords_seggregator.txt")
            
        self.model = ModelFactory.get_model(model_type, api_key, model_name)
        
    def load_prompt_template(self) -> str:
        try:
            with open(self.prompt_template_path,"r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt template not found at {self.prompt_template_path}")
        except Exception as e:
            raise Exception(f"Error loading prompt template: {str(e)}")
    
    
    def keywords_seggregator(self, restructured_query: str) -> str: 
        try:
            with open(self.prompt_template_path, "r", encoding="utf-8") as f:
                prompt = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found at {self.prompt_template_path}")
        
        formatted_prompt = prompt.format(re_structured_query = restructured_query)
        keywords_result = self.model.generate_content(formatted_prompt)
        # return keywords_result
        
        try: 
            
            return ast.literal_eval(keywords_result)   # better method to converting the keywords_result to dictionary
            
        except Exception as e:
            
            return -1    # return -1 if the keywords_result is not a valid dictionary
    
        
        # try:
        #     start_index = keywords_result.find("{")
        #     end_index = keywords_result.rfind("}") + 1
        #     json_content = keywords_result[start_index:end_index]
        #     keywords_result_dict = json.loads(json_content)
        #     return keywords_result_dict
        #     # return("Parsed JSON:", keywords_result_dict, "TYPE :  ", type(keywords_result_dict))
            
        # except json.JSONDecodeError as e:
        #     print("JSONDecodeError:", e)
        #     print("Invalid JSON content:", keywords_result)
        # except Exception as e:
        #     print("Error:", e)
        #     #print("Generated Content:", keywords_result)

# import json


# keywords_result = {}
# keywords_result = GM.generate_content(formatted_query_keywords_seggregator_template)
# print(keywords_result)
