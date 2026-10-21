from Rag_architecture.Loading import load_pdf
from Rag_architecture.chunking import split_documents
from Rag_architecture.indexing import index_documents, get_vector_store

import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )

def main():

    print("=== TEST RAG AVEC PGVECTOR ===")

    # 1. Charger le document
    documents = load_pdf("rag_test_novatech.pdf")


    # 2. Découper le document
    chunks = split_documents(documents)


    # 3. Indexer dans PostgreSQL
    index_documents(chunks)
    print("Indexation terminée !")

    # 4. Charger la base vectorielle
    vector_store = get_vector_store()

    # 5. Poser une question
    question = input("\nPose ta question : ")

    # 6. Recherche sémantique
    results = vector_store.similarity_search(
        query=question,
        k=3
    )

    # 7. Afficher les chunks retrouvés
    print("\n=== DOCUMENTS PERTINENTS ===")

    for i, doc in enumerate(results, start=1):
        print(f"\n--- Résultat {i} ---")
        print("Contenu :", doc.page_content)
        print("Source :", doc.metadata.get("source"))
        print("Page :", doc.metadata.get("page"))


if __name__ == "__main__":
    main()
