import uuid
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import DatabaseError, transaction
from django.db.models import Count
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .forms import DocumentUploadForm, MessageForm, RenameForm
from .document_imports import EmbeddingUnavailableError, import_document
from Rag_architecture.Loading import DocumentReadError
from .models import Conversation, Message
from Agent.Chatbot import answer_question

logger = logging.getLogger(__name__)


def page_context(request, conversation=None):
    conversations = request.user.conversations.annotate(message_count=Count("messages"))
    return {
        "conversations": conversations,
        "conversation": conversation,
        "chat_messages": conversation.messages.all() if conversation else [],
        "documents": conversation.documents.all() if conversation else [],
        "request_id": uuid.uuid4(),
    }


@login_required
@require_GET
def home(request):
    return render(request, "chat/workspace.html", page_context(request))


@login_required
@require_POST
def create(request):
    conversation = Conversation.objects.create(owner=request.user)
    return redirect(conversation)


@login_required
@require_GET
def detail(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk, owner=request.user)
    return render(request, "chat/workspace.html", page_context(request, conversation))


@login_required
@require_POST
def send_message(request, pk):
    wants_json = request.headers.get("Accept") == "application/json"
    form = MessageForm(request.POST)
    # Ownership is checked even for malformed submissions.
    conversation = get_object_or_404(Conversation, pk=pk, owner=request.user)
    if not form.is_valid():
        if wants_json:
            return JsonResponse({"error": "Saisissez un message de 1 à 10 000 caractères."}, status=400)
        messages.error(request, "Le message doit contenir entre 1 et 10 000 caractères.")
        context = page_context(request, conversation)
        context["draft"] = request.POST.get("content", "")[:10000]
        return render(request, "chat/workspace.html", context, status=400)

    with transaction.atomic():
        conversation = get_object_or_404(
            Conversation.objects.select_for_update(), pk=pk, owner=request.user,
        )
        message, created = Message.objects.get_or_create(
            conversation=conversation, request_id=form.cleaned_data["request_id"],
            defaults={"content": form.cleaned_data["content"], "role": Message.Role.USER},
        )
        if not created and (message.role != Message.Role.USER or message.content != form.cleaned_data["content"]):
            if wants_json:
                return JsonResponse({"error": "Cet envoi a déjà été enregistré. Rechargez la conversation."}, status=409)
            messages.error(request, "Cet envoi a déjà été enregistré. Vous pouvez écrire un nouveau message.")
            return redirect(conversation)
        if created:
            if conversation.title == "Nouvelle conversation" and conversation.messages.count() == 1:
                conversation.title = " ".join(message.content.split())[:120]
            conversation.save(update_fields=["title", "updated_at"])

    # A stable reply identifier makes retries idempotent, including concurrent retries.
    reply_id = uuid.uuid5(message.request_id, "assistant")
    reply = conversation.messages.filter(request_id=reply_id, role=Message.Role.ASSISTANT).first()
    error = None
    if reply is None:
        history = list(conversation.messages.filter(pk__lt=message.pk)
                       .order_by("-created_at", "-id").values_list("role", "content")[:12])
        history.reverse()
        try:
            answer = answer_question(
                message.content, user_id=request.user.pk,
                id_conversation=conversation.pk, history=history,
            )
            # Do not keep a database transaction open while the model generates the answer.
            with transaction.atomic():
                conversation = get_object_or_404(
                    Conversation.objects.select_for_update(), pk=pk, owner=request.user,
                )
                reply, _ = Message.objects.get_or_create(
                    conversation=conversation, request_id=reply_id,
                    defaults={"role": Message.Role.ASSISTANT, "content": answer},
                )
                conversation.save(update_fields=["updated_at"])
        except Http404:
            raise
        except Exception:
            logger.exception("Échec de la réponse du chatbot pour la conversation %s", pk)
            error = "Votre message est enregistré, mais le service de réponse est indisponible. Renvoyez le même message pour réessayer."

    def serialize(item):
        return {
            "id": item.pk, "content": item.content, "role": item.role,
            "time": timezone.localtime(item.created_at).strftime("%d/%m/%Y · %H:%M"),
        }

    if wants_json:
        return JsonResponse({
            "message": serialize(message),
            "reply": serialize(reply) if reply else None,
            "error": error,
            "title": conversation.title,
            "message_count": conversation.messages.count(),
            "next_request_id": str(message.request_id if error else uuid.uuid4()),
        }, status=503 if error else (201 if created else 200))
    if error:
        messages.error(request, error)
        context = page_context(request, conversation)
        context.update(draft=message.content, request_id=message.request_id)
        return render(request, "chat/workspace.html", context, status=503)
    return redirect(conversation)


@login_required
@require_POST
def rename(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk, owner=request.user)
    form = RenameForm(request.POST)
    if form.is_valid():
        conversation.title = form.cleaned_data["title"]
        conversation.save(update_fields=["title", "updated_at"])
        messages.success(request, "Le titre a été modifié.")
    else:
        messages.error(request, "Le titre doit contenir entre 1 et 120 caractères.")
    return redirect(conversation)


@login_required
@require_POST
def delete(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk, owner=request.user)
    conversation.delete()
    messages.success(request, "La conversation a été supprimée.")
    return redirect("chat:home")


@login_required
@require_POST
def upload_document(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk, owner=request.user)
    wants_json = request.headers.get("Accept") == "application/json"
    form = DocumentUploadForm(request.POST, request.FILES)
    error = None
    error_status = 400
    if not form.is_valid():
        error = " ".join(str(item) for errors in form.errors.values() for item in errors)
    elif len(request.FILES.getlist("document")) != 1:
        error = "Sélectionnez un seul document par import."
    else:
        try:
            imported, created = import_document(
                form.cleaned_data["document"], conversation=conversation, user=request.user,
            )
        except DocumentReadError as exc:
            error = str(exc)
        except EmbeddingUnavailableError as exc:
            error, error_status = str(exc), 503
        except Conversation.DoesNotExist as exc:
            raise Http404("La conversation n’existe plus.") from exc
        except DatabaseError:
            logger.exception("Échec de l’enregistrement de l’import")
            error = "L’enregistrement a échoué. Aucun import partiel n’a été conservé. Réessayez."
            error_status = 503
    if error:
        if wants_json:
            return JsonResponse({"error": error}, status=error_status)
        messages.error(request, error)
        return redirect(conversation)

    status_message = (
        f"{imported.filename} : {imported.chunk_count} passage(s) indexé(s)."
        if created else f"{imported.filename} est déjà importé dans cette conversation."
    )
    if wants_json:
        return JsonResponse({
            "message": status_message, "already_imported": not created,
            "document_count": conversation.documents.count(),
            "document": {
                "id": str(imported.pk), "filename": imported.filename,
                "chunk_count": imported.chunk_count, "size": imported.size,
                "date": timezone.localtime(imported.created_at).strftime("%d/%m/%Y · %H:%M"),
            },
        }, status=201 if created else 200)
    messages.success(request, status_message)
    return redirect(conversation)
