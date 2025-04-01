import requests
import numpy as np
from typing import List, Optional
from langchain_core.embeddings import Embeddings

class OllamaEmbeddings(Embeddings):
    """Ollama embeddings using nomic-embed-text."""
    
    def __init__(self, 
                 host: str = "localhost",
                 port: int = 11434,
                 model: str = "nomic-embed-text"):
        self.base_url = f"http://{host}:{port}/api/embeddings"
        self.model = model
        self.dimension = 768  # nomic-embed-text dimension
        
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of documents."""
        embeddings = []
        for text in texts:
            embedding = self._get_embedding(text)
            if embedding:
                embeddings.append(embedding)
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """Generate embedding for query text."""
        embedding = self._get_embedding(text)
        return embedding if embedding else [0.0] * self.dimension
        
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding from Ollama."""
        try:
            response = requests.post(
                self.base_url,
                json={
                    "model": self.model,
                    "prompt": text,
                }
            )
            response.raise_for_status()
            return response.json()["embedding"]
            
        except Exception as e:
            print(f"Embedding error: {str(e)}")
            return None 