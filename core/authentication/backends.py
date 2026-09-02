"""Backend de autenticacion por correo electronico o nombre de usuario."""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

UserModel = get_user_model()


class EmailOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get("email") or kwargs.get(UserModel.USERNAME_FIELD)
        if identifier is None or password is None:
            return None
        try:
            user = UserModel.objects.get(
                Q(email__iexact=identifier.strip()) | Q(username__iexact=identifier.strip()),
                deleted_at__isnull=True,
            )
        except UserModel.DoesNotExist:
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            user = (
                UserModel.objects.filter(
                    Q(email__iexact=identifier.strip()) | Q(username__iexact=identifier.strip())
                )
                .order_by("id")
                .first()
            )
            if user is None:
                return None

        if user.is_locked:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def user_can_authenticate(self, user):
        return bool(user.is_active and user.deleted_at is None)
