from abc import ABC, abstractmethod

class BaseModel(ABC):
    @abstractmethod
    def generate_content(self, prompt: str) -> str:
        """Generate content based on the prompt."""
        pass
