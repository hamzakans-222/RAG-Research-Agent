
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI

# Charger les variables d'environnement
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def load_system_prompt():
    return (
        Path(__file__).resolve().parent / "Prompt.txt"
    ).read_text(encoding="utf-8")


def create_chatbot():
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Configurez GOOGLE_API_KEY dans le fichier .env pour utiliser Gemini.")
    llm = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        google_api_key=api_key,
        max_output_tokens=4096,
        timeout=180,
        max_retries=2,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", load_system_prompt()),
        MessagesPlaceholder("history", optional=True),
        ("human", "{question}"),
    ])

    return prompt | llm
