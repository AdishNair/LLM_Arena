from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    provider: str

    @abstractmethod
    async def generate_response(self, model: str, prompt: str, context: list[dict] | None = None) -> str:
        raise NotImplementedError
