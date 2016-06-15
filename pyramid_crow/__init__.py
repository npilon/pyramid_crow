from pyramid.tweens import EXCVIEW
from pyramid.httpexceptions import WSGIHTTPException


def _handle_error(request):
    raise


def crow_tween_factory(handler, registry):
    def crow_tween(request):
        try:
            return handler(request)
        except WSGIHTTPException:
            raise
        except:
            _handle_error(request)
    return crow_tween


def includeme(config):
    config.add_tween('pyramid_crow.crow_tween_factory', under=EXCVIEW)
