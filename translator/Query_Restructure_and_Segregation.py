from typing import Optional
from pathlib import Path
from models.gemini import GeminiModel

class QueryRestructurer:
    def __init__(self, api_key: str, model_name: str, prompt_template_path: Path):
        """Initialize QueryRestructurer with configuration."""
        self.api_key = api_key
        self.model_name = model_name
        self.prompt_template_path = prompt_template_path
        self.model = GeminiModel(api_key=self.api_key, model_name=self.model_name)
        
    def load_prompt_template(self, template_path: Path) -> str:
        """Load prompt template from file."""
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt template not found at {template_path}")
        except Exception as e:
            raise Exception(f"Error loading prompt template: {str(e)}")

    def restructure_query(self, query: str) -> Optional[str]:
        """
        Restructure the user query using the prompt template.
        
        Args:
            query: Original user query
            
        Returns:
            Restructured query or None if processing fails
        """
        try:
            template = self.load_prompt_template(self.prompt_template_path)
            formatted_prompt = template.format(user_query=query)
            return self.model.generate_content(formatted_prompt)
        except Exception as e:
            print(f"Error restructuring query: {str(e)}")
            return None