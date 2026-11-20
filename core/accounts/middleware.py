from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect


class BanEnforcementMiddleware:
    """End existing sessions when their account is banned."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated and user.is_banned:
            logout(request)
            messages.error(request, 'Your account is currently banned.')
            return redirect('auth')
        return self.get_response(request)
