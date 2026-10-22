"""Compatibilité des anciens imports ; l'implémentation est centralisée."""
from Rag_architecture.indexing import (
    TABLE_NAME,
    VECTOR_SIZE,
    get_engine,
    get_vector_store,
    index_documents,
    search_documents,
)

__all__ = [
    "TABLE_NAME", "VECTOR_SIZE", "get_engine", "get_vector_store",
    "index_documents", "search_documents",
]
