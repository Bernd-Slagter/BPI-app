"""
Audit logging helpers.

Usage:
    from .audit import log_action
    log_action(request, 'job.created', job, 'Title: Senior Engineer')
"""
import logging

logger = logging.getLogger('ats.audit')


def log_action(request_or_user, action: str, obj=None, detail: str = ''):
    """
    Write one AuditLog row.

    request_or_user: HttpRequest (preferred) or a User instance or None.
    action: dot-namespaced string, e.g. 'job.created', 'ai.resume_parsed'.
    obj: the Django model instance being acted on (optional).
    detail: free-text extra context (old→new status, score, etc.).
    """
    from .models import AuditLog

    # Resolve user
    user = None
    if request_or_user is not None:
        if hasattr(request_or_user, 'user'):
            u = request_or_user.user
            if u and u.is_authenticated:
                user = u
        elif hasattr(request_or_user, 'is_authenticated'):
            if request_or_user.is_authenticated:
                user = request_or_user

    object_type = ''
    object_id = None
    object_repr = ''

    if obj is not None:
        object_type = type(obj).__name__
        if hasattr(obj, 'pk'):
            object_id = obj.pk
        object_repr = str(obj)[:250]

    try:
        AuditLog.objects.create(
            user=user,
            action=action,
            object_type=object_type,
            object_id=object_id,
            object_repr=object_repr,
            detail=detail,
        )
    except Exception:
        # Never let audit logging crash the main request
        logger.exception('Failed to write audit log entry: action=%s', action)

    # Also emit to the Python logger for external log aggregation
    logger.info(
        'action=%s user=%s object_type=%s object_id=%s repr=%r detail=%s',
        action,
        user.username if user else 'anonymous',
        object_type,
        object_id,
        object_repr,
        detail,
    )
