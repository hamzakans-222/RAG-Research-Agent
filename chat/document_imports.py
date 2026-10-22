import hashlib
import logging
from pathlib import PurePosixPath

from django.conf import settings
from django.db import connection, transaction

from Rag_architecture.Loading import DocumentReadError, load_document
from Rag_architecture.chunking import split_documents
from Rag_architecture.indexing import prepare_index, save_index

from .models import Conversation, ConversationDocument

logger = logging.getLogger(__name__)


class EmbeddingUnavailableError(Exception):
    pass


def import_document(uploaded, *, conversation, user):
    """Lecture → découpage → embeddings → écriture atomique des passages et de l'import."""
    if conversation.owner_id != user.pk:
        raise Conversation.DoesNotExist
    digest = hashlib.sha256()
    for part in uploaded.chunks():
        digest.update(part)
    file_hash = digest.hexdigest()
    existing = conversation.documents.filter(sha256=file_hash).first()
    if existing:
        return existing, False

    filename = PurePosixPath(uploaded.name.replace("\\", "/")).name
    documents = load_document(
        uploaded, filename=filename, max_pages=settings.DOCUMENT_UPLOAD_MAX_PAGES,
    )
    chunks = split_documents(documents)
    if not chunks:
        raise DocumentReadError("Aucun passage de texte à indexer dans ce document.")
    if len(chunks) > settings.DOCUMENT_UPLOAD_MAX_CHUNKS:
        raise DocumentReadError("Le document est trop long. Importez-le en plusieurs parties.")
    for position, chunk in enumerate(chunks):
        chunk.metadata["document_sha256"] = file_hash
        chunk.metadata["chunk_index"] = position

    try:
        prepared = prepare_index(chunks, user_id=user.pk, id_conversation=conversation.pk)
    except Exception as exc:
        logger.exception("Échec de la vectorisation du document")
        raise EmbeddingUnavailableError(
            "La vectorisation est indisponible. Vérifiez qu’Ollama est démarré "
            "avec le modèle nomic-embed-text, puis réessayez."
        ) from exc

    # Only the short database write is locked; inference does not hold a DB lock.
    with transaction.atomic():
        conversation = Conversation.objects.select_for_update().get(pk=conversation.pk, owner=user)
        existing = conversation.documents.filter(sha256=file_hash).first()
        if existing:
            return existing, False
        with connection.cursor() as cursor:
            chunk_count = save_index(prepared, cursor)
        imported = ConversationDocument.objects.create(
            conversation=conversation, filename=filename, sha256=file_hash,
            size=uploaded.size, chunk_count=chunk_count,
        )
        conversation.save(update_fields=["updated_at"])
    return imported, True
