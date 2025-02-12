import os
from dotenv import load_dotenv

load_dotenv()

# LLM Provider Settings
DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama2")

# Ollama Settings
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "localhost")
OLLAMA_PORT = os.getenv("OLLAMA_PORT", "11435")
OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"

# Model Parameters
DEFAULT_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
DEFAULT_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))