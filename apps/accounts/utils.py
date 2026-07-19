import re
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def rate_limit(limit=5, period=60):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated and request.user.is_admin:
                return view_func(request, *args, **kwargs)

            client_ip = get_client_ip(request)
            cache_key = f'rate_limit:{client_ip}:{view_func.__name__}'

            count = cache.get(cache_key, 0)

            if count >= limit:
                messages.error(request, f'Too many attempts. Please wait {period} seconds and try again.')
                if request.is_ajax():
                    return JsonResponse({
                        'error': 'Rate limit exceeded',
                        'message': f'Too many attempts. Please wait {period} seconds.'
                    }, status=429)
                return redirect(request.path)

            cache.set(cache_key, count + 1, period)

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def log_security_event(request, event_type, user_identifier=None):
    ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    try:
        from .models import SecurityLog
        SecurityLog.objects.create(
            event_type=event_type,
            ip_address=ip,
            user_agent=user_agent,
            user_identifier=user_identifier,
            path=request.path,
            method=request.method
        )
    except:
        print(f"[SECURITY] {timezone.now()} - {event_type} - IP: {ip} - User: {user_identifier} - Path: {request.path}")