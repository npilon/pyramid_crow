from pyramid.tweens import EXCVIEW
from pyramid.httpexceptions import WSGIHTTPException
from raven import Client


def crow_tween_factory(handler, registry):
    def crow_tween(request):
        try:
            return handler(request)
        except WSGIHTTPException:
            raise
        except:
            request.raven.captureException()
            raise

    return crow_tween


def _request_to_http_context(request):
    return {
        'method': request.method,
        'url': request.path_url,
        'query_string': request.query_string,
        'data': (
            request.body
            if request.content_length < 2**16
            else 'Over-long request body of {} bytes omitted'.format(
                request.content_length
            )
        ),
        'headers': dict(request.headers),
        'env': dict(request.environ),
    }


def raven_client(request):
    """Configure a raven client from pyramid config file, add request context

    Uses keys from the pyramid config file beginning with raven. and turns each
    into a kwarg to raven.Client. Also produces http context from request and
    adds to client's context"""
    kwargs = {}

    for key in request.registry.settings:
        if key.startswith('raven.'):
            kwarg = key.partition('.')[2]
            kwargs[kwarg] = request.registry.settings[key]

    client = Client(**kwargs)
    client.http_context(_request_to_http_context(request))

    return client


def includeme(config):
    config.add_request_method(raven_client, 'raven', reify=True)
    config.add_tween('pyramid_crow.crow_tween_factory', under=EXCVIEW)
