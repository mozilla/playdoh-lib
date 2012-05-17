from django_arecibo.arecibo import post as error
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.middleware.common import _is_ignorable_404
from django.utils.encoding import smart_unicode

import hashlib
import traceback
import sys
import uuid

NO_DEFAULT = object()

def arecibo_setting(key, default=NO_DEFAULT):
    arecibo_settings = getattr(settings, 'ARECIBO_SETTINGS', {})
    if default is NO_DEFAULT:
        return arecibo_settings[key]
    return arecibo_settings.get(key, default)

class Group(object):
    """Group together errors using Django caching lib."""
    # TODO: raise an error if they are using something
    # like locmem, which won't work.

    def __init__(self, hash):
        self.hash = hash
        self.data_key = 'arecibo-client-data:%s' % self.hash
        self.counter_key = 'arecibo-client-count:%s' % self.hash

    def set(self, data):
        if cache.get(self.data_key):
            cache.incr(self.counter_key)
        else:
            # First setting of the task, write a celery task to post
            # this in GROUP_WAIT seconds.
            from django_arecibo.tasks import delayed_send_group
            # We force a timeout so that if the original post fails and
            # never goes out, eventually the cache will clear again and
            # we've lost a few errors.
            cache.set_many({self.data_key: data, self.counter_key: 1},
                timeout=arecibo_setting('GROUP_WAIT', 60) * 2)
            delayed_send_group.apply_async([self.hash],
                countdown=arecibo_setting('GROUP_WAIT', 60))

    def delete(self, data):
        cache.delete_many([self.data_key, self.counter_key])

    @classmethod
    def get_hash(cls, *data):
        hash = hashlib.md5()
        hash.update(':'.join([str(d) for d in data]))
        return hash.hexdigest()

    @classmethod
    def find_group(cls, *data):
        return cls(cls.get_hash(*data))

    def send(self):
        data = cache.get_many([self.data_key, self.counter_key])
        if not data:
            return
        cache.delete_many([self.data_key, self.counter_key])
        self.post(data)

    def post(self, data):
        err = error()
        for key, value in data[self.data_key].items():
            err.set(key, value)
        err.set('count', data[self.counter_key])
        err.server(url=settings.ARECIBO_SERVER_URL)
        err.send()


class DjangoPost(object):
    def __init__(self, request, status, **kw):
        # first off, these items can just be ignored, we
        # really don't care about them too much
        path = request.get_full_path()
        if _is_ignorable_404(path):
            return

        # if you've set INTERNAL_IPS, we'll respect that and
        # ignore any requests, we suggest settings this so your
        # unit tests don't blast the server
        if request.META.get('REMOTE_ADDR') in settings.INTERNAL_IPS:
            return

        # You can optionally define some callbacks so that the error
        # will be tested against them before posting. This is good for
        # blocking certain user agents under certain conditions for examples.
        for callback in arecibo_setting('CALLBACKS', []):
            if callable(callback):
                fn = callback
            else:  # Should be a string, anything else is wrong.
                module, _, function = callback.rpartition('.')
                mod = __import__(module)
                fn = mod.getattr(function)
            if not fn(request, status):
                return

        exc_info = sys.exc_info()
        items = ['HOME', 'HTTP_ACCEPT', 'HTTP_ACCEPT_ENCODING', 'HTTP_REFERER', \
                 'HTTP_ACCEPT_LANGUAGE', 'HTTP_CONNECTION', 'HTTP_HOST', 'LANG', \
                 'PATH_INFO', 'QUERY_STRING', 'REQUEST_METHOD', 'SCRIPT_NAME', \
                 'SERVER_NAME', 'SERVER_PORT', 'SERVER_PROTOCOL', 'SERVER_SOFTWARE']
        data = [ "%s: %s" % (k, request.META[k]) for k in items if request.META.get(k)]
        if request.method.lower() == "post":
            data.append("POST and FILES Variables:")
            data.extend(["    %s: %s" % self.filter_post_var(k, v)
                         for k, v in request.POST.items()
                         if not self.exclude_post_var(k) ])
            data.extend(["    %s: %s" % self.filter_file(k, v)
                         for k, v in request.FILES.items()
                         if not self.exclude_file(k) ])

        # build out data to send to Arecibo some fields (like timestamp)
        # are automatically added
        self.data = {
            "account": getattr(settings, 'ARECIBO_PUBLIC_ACCOUNT_NUMBER', ''),
            "url": request.build_absolute_uri(),
            "ip": request.META.get('REMOTE_ADDR'),
            "traceback": u"\n".join(traceback.format_tb(exc_info[2])).encode("utf-8"),
            # Replace any chars that can't be represented in UTF-8 with the
            # Unicode replacement char:
            "request": "\n".join(smart_unicode(d, errors='replace') for d in data),
            "type": exc_info[0],
            "msg": str(exc_info[1]),
            "status": status,
            "uid": uuid.uuid4(),
            "user_agent": request.META.get('HTTP_USER_AGENT'),
        }

        # we might have a traceback, but it's not required
        try:
            if self.data["type"]:
                self.data["type"] = str(self.data["type"].__name__)
        except AttributeError:
            pass

        self.data.update(kw)

        # it could be the site does not have the standard django auth
        # setup and hence no request.user
        try:
            self.data["username"] = request.user.username,
            # this will be "" for Anonymous
        except Exception:
            pass

        # a 404 has some specific formatting of the error that can be useful
        if status == 404:
            msg = ""
            for m in exc_info[1]:
                if isinstance(m, dict):
                    tried = "\n".join(map(self.get_pattern, m["tried"]))
                    msg = "Failed to find %s, tried: \n%s" % (m["path"], tried)
                else:
                    msg += m
            self.data["msg"] = msg

        # if we don't get a priority, lets create one
        if not self.data.get("priority"):
            if status == 500: self.data["priority"] = 1
            else: self.data["priority"] = 5

        # populate my arecibo object
        self.err = error()
        for key, value in self.data.items():
            self.err.set(key, value)

    def get_pattern(self, obj):
        try:
            return str(obj[0].regex.pattern)
        except (IndexError, AttributeError):
            return str(obj)

    def exclude_post_var(self, name):
        return self.check_exclusions(arecibo_setting('EXCLUDED_POST_VARS', ()), name)

    def exclude_file(self, name):
        return self.check_exclusions(arecibo_setting('EXCLUDED_FILES', ()), name)

    def check_exclusions(self, exclusions, name):
        return name in exclusions

    def filter_post_var(self, name, value, mask_char='*'):
        filters = arecibo_setting('FILTERED_POST_VARS', ())
        if not name in filters:
            return name, value
        return name, mask_char[0] * len(value)

    def filter_file(self, name, value, mask_char='*'):
        filters = arecibo_setting('FILTERED_FILES', ())
        if not name in filters:
            return name, value

        return name, mask_chars[0] * len(name)

    def find_group(self, hash):
        return cache.get(hash)

    def _send_group(self):
        keys = ('type', 'msg', 'status')
        group = Group.find_group([self.data[k] for k in keys])
        group.set(self.data)

    def _send_no_group(self):
        try:
            self.err.server(url=settings.ARECIBO_SERVER_URL)
            self.err.send()
        except Exception, e:
            # If you want this to be an explicit, uncomment the following.
            #print "Hit an exception sending: %s" % error
            #raise
            pass

    def send(self):
        if arecibo_setting('GROUP_POSTS', False):
            return self._send_group()
        return self._send_no_group()


def post(request, status, **kw):
    obj = DjangoPost(request, status, **kw)
    if obj and hasattr(obj, 'data'):
        obj.send()
        return obj.data.get("uid")
