from pypdf import PdfReader
from langchain_core.documents import Document
from pathlib import Path


class DocumentReadError(ValueError):
    """Document invalide ou non pris en charge."""


def load_pdf(path, *, source=None, max_pages=None, max_characters=None):
    reader = PdfReader(path)
    if reader.is_encrypted:
        raise DocumentReadError("Les PDF protégés par mot de passe ne sont pas pris en charge.")
    if max_pages and len(reader.pages) > max_pages:
        raise DocumentReadError(f"Le PDF dépasse la limite de {max_pages} pages.")
    documents = []
    character_count = 0

    for i, page in enumerate(reader.pages):
        text = page.extract_text()

        if text and text.strip():
            character_count += len(text)
            if max_characters and character_count > max_characters:
                raise DocumentReadError("Le document contient trop de texte. Importez-le en plusieurs parties.")
            documents.append(
                Document(
                    page_content=text,
                    metadata={
                        "source": source or str(path),
                        "page": i
                    }
                )
            )

    return documents


def load_document(uploaded, *, filename, max_pages=200, max_characters=500000):
    """Charger un fichier reçu en mémoire ou sur disque temporaire, sans le publier."""
    suffix = Path(filename).suffix.lower()
    uploaded.seek(0)
    if suffix == ".pdf":
        if uploaded.read(5) != b"%PDF-":
            raise DocumentReadError("Le fichier sélectionné n’est pas un PDF valide.")
        uploaded.seek(0)
        try:
            documents = load_pdf(
                uploaded, source=filename, max_pages=max_pages,
                max_characters=max_characters,
            )
        except DocumentReadError:
            raise
        except Exception as exc:
            raise DocumentReadError("Impossible de lire ce PDF. Vérifiez qu’il n’est pas endommagé.") from exc
    elif suffix in {".txt", ".md"}:
        try:
            text = uploaded.read().decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DocumentReadError("Le fichier texte doit être enregistré en UTF-8.") from exc
        if "\x00" in text:
            raise DocumentReadError("Le fichier contient des données binaires, pas du texte.")
        if len(text) > max_characters:
            raise DocumentReadError("Le document contient trop de texte. Importez-le en plusieurs parties.")
        documents = [Document(page_content=text, metadata={"source": filename, "page": 0})] if text.strip() else []
    else:
        raise DocumentReadError("Formats acceptés : PDF, TXT et Markdown (.md).")
    if not documents:
        raise DocumentReadError("Aucun texte lisible trouvé. Un PDF scanné doit d’abord être converti en texte par OCR.")
    return documents
