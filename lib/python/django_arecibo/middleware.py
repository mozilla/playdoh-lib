from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django_arecibo.wrapper import post

has_celery = True
try:
    from django_arecibo.tasks import post as delayed_post
except ImportError, e:
    has_celery = False


def arecibo_post(method, request, exception):
    if getattr(settings, 'ARECIBO_SERVER_URL', ''):
        if isinstance(exception, Http404):
            method(request, 404)
        else:
            method(request, 500)

class AreciboMiddleware(object):

    def process_exception(self, request, exception):
        return arecibo_post(post, request, exception)

class AreciboMiddlewareCelery(object):

    def __init__(self):
        if not has_celery:
            raise ImproperlyConfigured('Cannot use AreciboMiddlewareCelery '
                                       'if Celery is not installed.')

    def process_exception(self, request, exception):
        return arecibo_post(delayed_post, request, exception)
