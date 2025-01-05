from .gemini import GeminiModel
from .openai import ModelOpenAI

class ModelFactory:
    @staticmethod
    def get_model(model_type: str, api_key: str, model_name: str):
        if model_type.lower() == "gemini":
            
            return GeminiModel(api_key, model_name)
        
        elif model_type.lower() == "openai":
            
            return ModelOpenAI(model_name, api_key)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
