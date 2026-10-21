from langchain_ollama import OllamaEmbeddings

def get_embedding_model():
    model = OllamaEmbeddings(
        model="nomic-embed-text:latest",
        base_url="http://localhost:11434"
    )
    return model