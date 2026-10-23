
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_anthropic import ChatAnthropic

# Charger les variables d'environnement
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def load_system_prompt():
    return (
        Path(__file__).resolve().parent / "Prompt.txt"
    ).read_text(encoding="utf-8")


def create_chatbot():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("Configurez ANTHROPIC_API_KEY dans le fichier .env pour utiliser Claude.")
    llm = ChatAnthropic(
        model=os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5"),
        api_key=api_key,
        max_tokens=4096,
        timeout=180,
        max_retries=2,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", load_system_prompt()),
        MessagesPlaceholder("history", optional=True),
        ("human", "{question}"),
    ])

    return prompt | llm
