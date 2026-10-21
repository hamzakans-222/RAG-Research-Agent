from pypdf import PdfReader
from langchain_core.documents import Document

def load_pdf(path):
    reader = PdfReader(path)
    documents = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text()

        if text and text.strip():
            documents.append(
                Document(
                    page_content=text,
                    metadata={
                        "source": path,
                        "page": i
                    }
                )
            )

    return documents
