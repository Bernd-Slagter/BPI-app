from django.conf import settings
from django.shortcuts import redirect


class LoginRequiredMiddleware:
    """Redirect unauthenticated users to the login page for every view."""

    EXEMPT_PREFIXES = ('/accounts/', '/admin/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            path = request.path_info
            if not any(path.startswith(p) for p in self.EXEMPT_PREFIXES):
                return redirect(f"{settings.LOGIN_URL}?next={request.path}")
        return self.get_response(request)
