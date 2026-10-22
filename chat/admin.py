from django.contrib import admin

from .models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["title", "owner", "created_at", "updated_at"]
    list_filter = ["created_at"]
    search_fields = ["title", "owner__username"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "conversation", "role", "created_at"]
    list_filter = ["role"]
    search_fields = ["content", "conversation__owner__username"]
    readonly_fields = ["created_at", "request_id"]
