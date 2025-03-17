from .gemini import GeminiModel
from .openai import ModelOpenAI
import os

class ModelFactory:
    @staticmethod
    def get_model(model_type: str, api_key: str, model_name: str):
        try:
            if model_type.lower() == "gemini":
                return GeminiModel(api_key, model_name)
            elif model_type.lower() == "openai":
                return ModelOpenAI(model_name, api_key)
            else:
                # If unsupported model type, try OpenAI as fallback
                openai_api_key = os.getenv("OPENAI_API_KEY")
                if openai_api_key:
                    return ModelOpenAI("gpt-3.5-turbo", openai_api_key)
                raise ValueError(f"Unsupported model type: {model_type} and no fallback available")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize model: {e}")
