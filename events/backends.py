from django.contrib.auth.backends import ModelBackend
from .models import User


class EmailOrUsernameBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in
    using either their email address or their username.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        # Try to find user by email first, then fall back to username
        try:
            user = User.objects.get(email__iexact=username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(username__iexact=username)
            except User.DoesNotExist:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
