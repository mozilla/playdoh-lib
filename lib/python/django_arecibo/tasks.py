from celery.decorators import task


@task
def delayed_send_group(hash, **kw):
    from wrapper import Group
    Group(hash).send()


@task
def delayed_send(obj, **kw):
    obj.send()


def post(request, status, **kw):
    from wrapper import DjangoPost
    obj = DjangoPost(request, status, **kw)
    if obj and hasattr(obj, 'data'):
        delayed_send.delay(obj)
        return obj.data.get('uid')
