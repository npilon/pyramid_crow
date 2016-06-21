import sys

from pyramid.tweens import EXCVIEW
from pyramid.settings import aslist
from pyramid.settings import asbool
from pyramid.httpexceptions import WSGIHTTPException
from pyramid.util import DottedNameResolver
from pyramid.events import (
    NewRequest,
    subscriber,
)

from raven import Client

import logging
logger = logging.getLogger(__name__)

resolver = DottedNameResolver(None)

PY3 = sys.version_info[0] == 3

if PY3: # pragma: no cover
    import builtins
else:
    import __builtin__ as builtins

CLEAR_CONTEXT_FLAG = "pyramid_crow.clear"


def as_globals_list(value):
    L = []
    value = aslist(value)
    for dottedname in value:
        if dottedname in builtins.__dict__:
            if PY3: # pragma: no cover
                dottedname = 'builtins.%s' % dottedname
            else:
                dottedname = '__builtin__.%s' % dottedname
        obj = resolver.resolve(dottedname)
        L.append(obj)
    return L


def crow_tween_factory(handler, registry):

    get = registry.settings.get

    ignored = get('pyramid_crow.ignore', tuple())
    if WSGIHTTPException not in ignored:
        ignored = ignored + (WSGIHTTPException,)

    def crow_tween(request):
        try:
            return handler(request)
        except ignored:
            raise
        except:
            request.raven.captureException()
            raise

    return crow_tween


def _filter_request_body(request):
    """Ensure we don't send an over-long request body to sentry

    65 KB is probably enough for anybody"""
    if request.content_length is None:
        # No content_length - pass through whatever we got.
        return request.body
    elif request.content_length >= 2 ** 16:
        return 'Over-long request body of {} bytes omitted'.format(
            request.content_length
        )
    else:
        return request.body


def _request_to_http_context(request):
    return {
        'method': request.method,
        'url': request.path_url,
        'query_string': request.query_string,
        'data': _filter_request_body(request),
        'headers': dict(request.headers),
        'env': dict(request.environ),
    }


def _raven(request):
    client = request.registry["raven.client"]
    clear_after = request.environ.get(CLEAR_CONTEXT_FLAG, True)
    client.http_context(_request_to_http_context(request))
    if clear_after:
        request.add_finished_callback(lambda r: r.raven.context.clear())
    return client


def raven_client(registry):
    """Configure a raven client from pyramid config file, add request context

    Uses keys from the pyramid config file beginning with raven. and turns each
    into a kwarg to raven.Client. Also produces http context from request and
    adds to client's context"""
    kwargs = {
        'processors': (
            'pyramid_crow.processors.PyramidSanitizePasswordsProcessor',
        ),
        'timeout': 4,
    }

    for key in registry.settings:
        if key.startswith('raven.'):
            kwarg = key.partition('.')[2]
            kwargs[kwarg] = registry.settings[key]

    client = Client(**kwargs)
    return client


@subscriber(NewRequest)
def add_http_context(event):
    client = event.request.raven
    client.http_context(_request_to_http_context(event.request))


def includeme(config):
    get = config.registry.settings.get
    ignored = as_globals_list(get('pyramid_crow.ignore',
                              'pyramid.httpexceptions.WSGIHTTPException'))

    config.registry.settings['pyramid_crow.ignore'] = tuple(ignored)

    client = raven_client(config.registry)
    config.registry['raven.client'] = client

    config.add_request_method(_raven, 'raven', reify=True)
    config.add_tween('pyramid_crow.crow_tween_factory', under=EXCVIEW)
    config.scan()
