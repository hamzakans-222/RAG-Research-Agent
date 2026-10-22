import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations",
    )
    title = models.CharField("titre", max_length=120, default="Nouvelle conversation")
    created_at = models.DateTimeField("créée le", auto_now_add=True)
    updated_at = models.DateTimeField("modifiée le", auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [models.Index(fields=["owner", "-updated_at"], name="chat_owner_updated_idx")]
        constraints = [
            models.UniqueConstraint(fields=["id", "owner"], name="chat_conversation_owner_pair"),
        ]
        verbose_name = "conversation"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("chat:detail", args=[self.pk])


class Message(models.Model):
    class Role(models.TextChoices):
        USER = "user", "Utilisateur"
        ASSISTANT = "assistant", "Assistant"

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages",
    )
    role = models.CharField("auteur", max_length=10, choices=Role.choices, default=Role.USER)
    content = models.TextField("contenu", max_length=10000)
    created_at = models.DateTimeField("envoyé le", auto_now_add=True)
    request_id = models.UUIDField(default=uuid.uuid4, editable=False)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(fields=["conversation", "request_id"], name="chat_unique_submission"),
            models.CheckConstraint(condition=models.Q(role__in=["user", "assistant"]), name="chat_valid_role"),
            models.CheckConstraint(condition=~models.Q(content=""), name="chat_nonempty_message"),
        ]
        verbose_name = "message"

    def __str__(self):
        return f"{self.get_role_display()} : {self.content[:60]}"


class ConversationDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="documents")
    filename = models.CharField("nom du fichier", max_length=255)
    sha256 = models.CharField("empreinte du fichier", max_length=64)
    size = models.PositiveIntegerField("taille en octets")
    chunk_count = models.PositiveIntegerField("nombre de passages")
    created_at = models.DateTimeField("importé le", auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["conversation", "sha256"], name="chat_unique_document_content"),
        ]
        verbose_name = "document importé"
        verbose_name_plural = "documents importés"

    def __str__(self):
        return self.filename
