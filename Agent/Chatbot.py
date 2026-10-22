"""Entry point shared by the Django chatbot and the local command line."""
from functools import lru_cache

from Agent.Agent import create_chatbot
from Agent.Retriver import generate_answer
from Rag_architecture.indexing import get_vector_store


@lru_cache(maxsize=1)
def _resources():
    return get_vector_store(), create_chatbot()


def answer_question(question, *, user_id, id_conversation, history=()):
    vector_store, chain = _resources()
    return generate_answer(
        question, vector_store, chain, user_id=user_id,
        id_conversation=id_conversation, history=history,
    )


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Chatbot RAG local")
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--conversation-id", required=True)
    args = parser.parse_args()
    history = []
    print("=== CHATBOT RAG ===\nTape 'exit' pour quitter.\n")
    while True:
        question = input("Vous : ").strip()
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue
        try:
            answer = answer_question(
                question, user_id=args.user_id, id_conversation=args.conversation_id,
                history=history,
            )
            print(f"\nAssistant : {answer}\n")
            history = [*history, ("user", question), ("assistant", answer)][-12:]
        except Exception as exc:
            print(f"Erreur : {exc}")


if __name__ == "__main__":
    main()
