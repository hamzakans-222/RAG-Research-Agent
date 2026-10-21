import os
from uuid import NAMESPACE_URL, uuid5
from dotenv import load_dotenv
from psycopg.errors import DuplicateTable
from sqlalchemy.engine import URL
from sqlalchemy.exc import ProgrammingError
from langchain_postgres import PGEngine, PGVectorStore

from .Embedding import get_embedding_model

load_dotenv()

TABLE_NAME = "rag_documents"
VECTOR_SIZE = 768


def get_engine():
    """Créer une connexion à PostgreSQL."""

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
    """Ouvrir la table pgvector existante."""

    engine = get_engine()

    vector_store = PGVectorStore.create_sync(
        engine=engine,
        table_name=TABLE_NAME,
        embedding_service=get_embedding_model()
    )

    return vector_store


def index_documents(chunks):
    """Indexer les chunks dans PostgreSQL."""

    if not chunks:
        print("Aucun chunk à indexer.")
        return

    engine = get_engine()

    try:
        engine.init_vectorstore_table(table_name=TABLE_NAME, vector_size=VECTOR_SIZE)
    except ProgrammingError as exc:
        if not isinstance(exc.orig, DuplicateTable):
            raise

    vector_store = PGVectorStore.create_sync(
        engine=engine,
        table_name=TABLE_NAME,
        embedding_service=get_embedding_model()
    )

    chunk_ids = [
        str(uuid5(NAMESPACE_URL, repr((chunk.metadata, chunk.page_content))))
        for chunk in chunks
    ]
    ids = vector_store.add_documents(chunks, ids=chunk_ids)

    print(f"{len(ids)} chunks stockés dans PostgreSQL.")

    return vector_store
