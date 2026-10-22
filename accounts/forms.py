from django.contrib.auth.forms import AuthenticationForm, UserCreationForm


class SignupForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({
            "placeholder": "Choisissez un nom d’utilisateur", "autocomplete": "username",
        })
        self.fields["password1"].widget.attrs.update({
            "placeholder": "Créez un mot de passe", "autocomplete": "new-password",
        })
        self.fields["password2"].widget.attrs.update({
            "placeholder": "Confirmez votre mot de passe", "autocomplete": "new-password",
        })


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({
            "placeholder": "Votre nom d’utilisateur", "autocomplete": "username",
        })
        self.fields["password"].widget.attrs.update({
            "placeholder": "Votre mot de passe", "autocomplete": "current-password",
        })
