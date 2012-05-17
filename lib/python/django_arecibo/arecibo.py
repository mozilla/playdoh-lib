# -*- coding: utf-8 -*-
from django.utils import simplejson as json

from httplib import HTTPConnection
has_https = False
try:
    from httplib import HTTPSConnection
    has_https = True
except ImportError:
    pass

from urllib import urlencode
from urlparse import urlparse
try:
    from socket import gethostname, getdefaulttimeout, setdefaulttimeout
except ImportError:
    # App Engine doesn't have these
    # so here are a some replacements
    def gethostname(): return "unknown"
    def getdefaulttimeout(): return 60
    def setdefaulttimeout(num): pass

from email.Utils import formatdate

import smtplib

keys = ["account", "ip", "priority", "uid",
    "type", "msg", "traceback", "user_agent",
    "url", "status", "server", "timestamp",
    "request", "username", "count"]

default_route = "/v/1/"

class post:
    def __init__(self):
        self._data = {}
        self.transport = "http"
        self.smtp_server = "localhost"
        self.smtp_from = "noreply@clearwind.ca"
        self.url = None
        self.smtp_to = None
        self.set("server", gethostname())
        self.set("timestamp", formatdate())

    # public
    def set(self, key, value):
        """ Sets the variable named key, with the value """
        if key not in keys:
            raise ValueError, "Unknown value: %s" % key
        self._data[key] = value

    def server(self, url=None, email=None):
        """ Sets the URL or address so we know where to post the error """
        if url: self.url = urlparse(url)
        if email: self.smtp_to = email

    def send(self):
        """ Sends the data to the arecibo server """
        self._send()

    def as_json(self):
        return json.dumps(self._data)

    # private
    def _data_encoded(self):
        data = {}
        for k in keys:
            if self._data.get(k):
                data[k] = self._data.get(k)
        return urlencode(data)

    def _send(self):
        key = self.transport.lower()
        assert key in ["http", "smtp", "https"]
        if key in ["http", "https"]:
            assert self.url, "No URL is set to post the error to."
            self._send_http()
        elif key == "smtp":
            assert self.smtp_to, "No destination email is set to post the error to."
            self._send_smtp()

    def _msg_body(self):
        msg = "From: %s\r\nTo: %s\r\n\r\n%s" % (self.smtp_from, self.smtp_to, self.as_json())
        return msg

    def _send_smtp(self):
        msg = self._msg_body()
        s = smtplib.SMTP(self.smtp_server)
        s.sendmail(self.smtp_from, self.smtp_to, msg)
        s.quit()

    def _send_http(self):
        if self.transport == "https" and has_https:
            h = HTTPSConnection(self.url[1])
        else:
            h = HTTPConnection(self.url[1])
        headers = {
            "Content-type": 'application/x-www-form-urlencoded; charset="utf-8"',
            "Accept": "text/plain"}
        data = self._data_encoded()
        oldtimeout = getdefaulttimeout()
        try:
            setdefaulttimeout(10)
            h.request("POST", default_route, data, headers)

            reply = h.getresponse()
            if reply.status != 200:
                raise ValueError, "%s (%s)" % (reply.read(), reply.status)
        finally:
            setdefaulttimeout(oldtimeout)
