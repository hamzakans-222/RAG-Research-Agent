from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from .forms import LoginForm
from .views import signup

app_name = "accounts"
urlpatterns = [
    path("inscription/", signup, name="signup"),
    path("connexion/", LoginView.as_view(
        template_name="accounts/login.html", authentication_form=LoginForm,
        redirect_authenticated_user=True,
    ), name="login"),
    path("deconnexion/", LogoutView.as_view(), name="logout"),
]
