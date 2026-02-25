import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    llama_cloud_api_key: str
    openai_model: str = "gpt-4o-mini"

def load_settings() -> Settings:
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    llama_key = os.getenv("LLAMA_CLOUD_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

    if not openai_api_key:
        raise ValueError("Missing OPENAI_API_KEY in environment.")
    if not llama_key:
        raise ValueError("Missing LLAMA_CLOUD_API_KEY in environment.")

    return Settings(
        openai_api_key=openai_api_key,
        llama_cloud_api_key=llama_key,
        openai_model=model,
    )
