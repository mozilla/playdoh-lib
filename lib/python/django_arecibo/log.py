import logging
from django.conf import settings
from django_arecibo.tasks import post


class AreciboHandler(logging.Handler):
    """An exception log handler that sends tracebacks to Arecibo."""
    def emit(self, record):
        arecibo = getattr(settings, 'ARECIBO_SERVER_URL', '')

        if arecibo and hasattr(record, 'request'):
            post(record.request, 500)
