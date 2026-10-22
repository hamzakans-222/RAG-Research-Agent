import os
import asyncio
import sys
import json
import math
from dataclasses import dataclass
from uuid import NAMESPACE_URL, UUID, uuid5
from dotenv import load_dotenv
from langchain_core.documents import Document
from sqlalchemy.engine import URL
from langchain_postgres import PGEngine, PGVectorStore

from .Embedding import get_embedding_model

load_dotenv()

TABLE_NAME = "rag_documents"
VECTOR_SIZE = 768


def get_engine():
    """Créer une connexion à PostgreSQL."""

    # Psycopg needs a selector loop on Windows, independently of the chat provider.
    if sys.platform == "win32" and isinstance(
        asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy,
    ):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    connection = URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT", "15432")),
        database=os.getenv("POSTGRES_DB")
    )

    engine = PGEngine.from_connection_string(
        url=connection.render_as_string(hide_password=False)
    )

    return engine


def get_vector_store():
    """Ouvrir la table créée par manage.py migrate (accès bas niveau)."""

    engine = get_engine()

    vector_store = PGVectorStore.create_sync(
        engine=engine,
        table_name=TABLE_NAME,
        embedding_service=get_embedding_model(),
        metadata_columns=["user_id", "id_conversation"],
    )

    return vector_store


def _normalize_scope(user_id, id_conversation):
    if user_id is None and id_conversation is None:
        return None
    if user_id is None or id_conversation is None:
        raise ValueError("user_id et id_conversation doivent être fournis ensemble.")
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id < 1:
        raise ValueError("user_id doit être un identifiant utilisateur entier positif.")
    return {"user_id": user_id, "id_conversation": str(UUID(str(id_conversation)))}


def index_documents(chunks, *, user_id=None, id_conversation=None):
    """Indexer des passages, éventuellement rattachés à un compte et une conversation.

    Sans identifiants, les passages restent non attribués (démonstration historique).
    Les clés étrangères vérifient que la conversation appartient bien au compte.
    """

    scope = _normalize_scope(user_id, id_conversation)

    if not chunks:
        print("Aucun chunk à indexer.")
        return

    prepared, chunk_ids = _prepare_documents(chunks, scope)
    vector_store = get_vector_store()
    ids = vector_store.add_documents(prepared, ids=chunk_ids)

    print(f"{len(ids)} chunks stockés dans PostgreSQL.")
    return vector_store


def _prepare_documents(chunks, scope):

    # A document reused in two conversations must not overwrite the first copy.
    # Ownership comes from explicit arguments, never from document metadata.
    prepared = []
    chunk_ids = []
    for chunk in chunks:
        metadata = {key: value for key, value in chunk.metadata.items()
                    if key not in {"user_id", "id_conversation"}}
        identity = (metadata, chunk.page_content)
        if scope:
            identity = (scope["user_id"], scope["id_conversation"], *identity)
        chunk_ids.append(str(uuid5(NAMESPACE_URL, repr(identity))))
        prepared.append(Document(page_content=chunk.page_content, metadata={
            **metadata, **(scope or {"user_id": None, "id_conversation": None}),
        }))

    return prepared, chunk_ids


@dataclass
class PreparedIndex:
    documents: list[Document]
    ids: list[str]
    embeddings: list[list[float]]


def prepare_index(chunks, *, user_id, id_conversation):
    """Calculer les vecteurs avant d'ouvrir la transaction PostgreSQL de l'import."""
    scope = _normalize_scope(user_id, id_conversation)
    if scope is None or not chunks:
        raise ValueError("Un import nécessite des passages, un utilisateur et une conversation.")
    documents, ids = _prepare_documents(chunks, scope)
    model = get_embedding_model()
    embeddings = []
    for start in range(0, len(documents), 16):
        batch = documents[start:start + 16]
        vectors = model.embed_documents([doc.page_content for doc in batch])
        if len(vectors) != len(batch):
            raise ValueError("Le nombre de vecteurs retournés est incorrect.")
        for vector in vectors:
            if len(vector) != VECTOR_SIZE or not all(math.isfinite(value) for value in vector):
                raise ValueError("Les vecteurs doivent contenir 768 valeurs numériques finies.")
        embeddings.extend(vectors)
    return PreparedIndex(documents=documents, ids=ids, embeddings=embeddings)


def save_index(prepared, cursor):
    """Enregistrer tout l'import dans la transaction fournie par l'appelant."""
    if not (len(prepared.documents) == len(prepared.ids) == len(prepared.embeddings)):
        raise ValueError("Index incomplet.")
    rows = []
    for document_id, document, embedding in zip(prepared.ids, prepared.documents, prepared.embeddings):
        metadata = document.metadata.copy()
        user_id = metadata.pop("user_id")
        conversation_id = metadata.pop("id_conversation")
        rows.append((
            document_id, document.page_content, json.dumps(embedding, allow_nan=False),
            json.dumps(metadata, ensure_ascii=False), user_id, conversation_id,
        ))
    cursor.executemany(
        "INSERT INTO public.rag_documents "
        "(langchain_id, content, embedding, langchain_metadata, user_id, id_conversation) "
        "VALUES (%s, %s, %s::vector, %s::json, %s, %s) "
        "ON CONFLICT (langchain_id) DO UPDATE SET "
        "content=EXCLUDED.content, embedding=EXCLUDED.embedding, "
        "langchain_metadata=EXCLUDED.langchain_metadata, "
        "user_id=EXCLUDED.user_id, id_conversation=EXCLUDED.id_conversation",
        rows,
    )
    return len(rows)


def search_documents(question, *, user_id, id_conversation, k=3):
    """Rechercher uniquement les passages du compte et de la conversation indiqués."""
    scope = _normalize_scope(user_id, id_conversation)
    if scope is None:
        raise ValueError("Les identifiants du compte et de la conversation sont requis.")
    return get_vector_store().similarity_search(query=question, k=k, filter=scope)
