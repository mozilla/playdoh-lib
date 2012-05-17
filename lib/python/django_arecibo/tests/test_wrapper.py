# Tell Django where its settings are so its imports don't freak out. Factor
# this up when we get more test modules.
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'django_arecibo.tests.settings'

from django.test import RequestFactory

from django_arecibo.wrapper import DjangoPost


def test_unicode_in_request():
    """Instantiating a post with a request containing unicode meta vars shouldn't crash."""
    try:
        booga  # DjangoPost constructor expects some exception info around.
    except NameError:
        DjangoPost(RequestFactory().get('/hi', QUERY_STRING='\xc2'), 404)
