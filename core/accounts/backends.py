from django.contrib.auth.backends import ModelBackend


class BanAwareModelBackend(ModelBackend):
    """Reject active bans in Django's standard authentication flows."""

    def user_can_authenticate(self, user):
        return super().user_can_authenticate(user) and not user.is_banned
