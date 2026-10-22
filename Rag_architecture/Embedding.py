from langchain_ollama import OllamaEmbeddings
import os

def get_embedding_model():
    model = OllamaEmbeddings(
        model="nomic-embed-text:latest",
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        client_kwargs={"timeout": 120.0},
    )
    return model
