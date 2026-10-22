from django.urls import path

from . import views

app_name = "chat"
urlpatterns = [
    path("", views.home, name="home"),
    path("conversations/nouvelle/", views.create, name="create"),
    path("conversations/<uuid:pk>/", views.detail, name="detail"),
    path("conversations/<uuid:pk>/messages/", views.send_message, name="send"),
    path("conversations/<uuid:pk>/documents/", views.upload_document, name="upload"),
    path("conversations/<uuid:pk>/renommer/", views.rename, name="rename"),
    path("conversations/<uuid:pk>/supprimer/", views.delete, name="delete"),
]
