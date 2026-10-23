from uuid import UUID


def generate_answer(question, vector_store, chain, *, user_id, id_conversation, history=()):
    """Retrieve only this account's documents in this conversation."""
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id < 1:
        raise ValueError("Identifiant utilisateur invalide.")
    scope = {"user_id": user_id, "id_conversation": str(UUID(str(id_conversation)))}
    history = list(history)[-12:]
    # Recent questions help resolve follow-ups such as « et sa date ? ».
    previous_questions = [text for role, text in history if role == "user"][-2:]
    query = "\n".join([*(text[:1000] for text in previous_questions), question])
    documents = vector_store.similarity_search(query=query, k=3, filter=scope)
    if not documents:
        return "Aucun document n’est disponible dans cette conversation. Importez un document pour que je puisse répondre à vos questions."
    context = "\n\n".join(
        f"[Document {i} — {doc.metadata.get('source', 'document importé')}]\n{doc.page_content[:6000]}"
        for i, doc in enumerate(documents, start=1)
    )
    response = chain.invoke({
        "context": context, "question": question,
        "history": [(role, text[:1500]) for role, text in history],
    })
    # The model may return content blocks; .text extracts only the answer text.
    answer = response.text
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Le modèle a retourné une réponse vide.")
    return answer.strip()[:10000]
