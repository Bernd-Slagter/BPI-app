from django.apps import AppConfig


class AtsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ats'
    verbose_name = 'Application Tracking System'

    def ready(self):
        from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed

        def on_login(sender, request, user, **kwargs):
            from .audit import log_action
            log_action(request, 'auth.login', user, f'Login from {_get_ip(request)}')

        def on_logout(sender, request, user, **kwargs):
            from .audit import log_action
            log_action(request, 'auth.logout', user)

        def on_login_failed(sender, credentials, request, **kwargs):
            from .audit import log_action
            username = credentials.get('username', '?')
            log_action(request, 'auth.login_failed', detail=f'Username: {username} from {_get_ip(request)}')

        user_logged_in.connect(on_login)
        user_logged_out.connect(on_logout)
        user_login_failed.connect(on_login_failed)


def _get_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '?')
