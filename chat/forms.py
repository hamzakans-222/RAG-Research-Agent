from django import forms
from django.conf import settings
from pathlib import Path


class MessageForm(forms.Form):
    content = forms.CharField(max_length=10000, strip=True)
    request_id = forms.UUIDField()


class RenameForm(forms.Form):
    title = forms.CharField(label="Titre", max_length=120, strip=True)


class DocumentUploadForm(forms.Form):
    document = forms.FileField(label="Document", max_length=255)

    def clean_document(self):
        document = self.cleaned_data["document"]
        if Path(document.name).suffix.lower() not in {".pdf", ".txt", ".md"}:
            raise forms.ValidationError("Formats acceptés : PDF, TXT et Markdown (.md).")
        if document.size > settings.DOCUMENT_UPLOAD_MAX_BYTES:
            raise forms.ValidationError("Le fichier dépasse la taille maximale de 10 Mo.")
        return document
