import unittest
from pyramid import (
    testing,
    httpexceptions,
)
from raven.utils import json
from webtest import TestApp
import mock

import pyramid_crow


class ExpectedException(Exception):
    pass


class IgnoredException(Exception):
    pass


class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp(
            settings={
                'raven.dsn': 'https://foo:bar@example.com/notadsn',
            }
        )

    def tearDown(self):
        testing.tearDown()

    def _makeApp(self):
        self.config.include('pyramid_crow')
        app = self.config.make_wsgi_app()
        return TestApp(app)

    def test_noop(self):
        config = self.config

        def view(request):
            return 'ok'

        config.add_view(view, name='', renderer='string')

        app = self._makeApp()

        with mock.patch.object(pyramid_crow.Client,
                               'captureException') as mock_capture:
            resp = app.get('/')

        mock_capture.assert_not_called()
        self.assertEqual(resp.body, b'ok')

    def test_ignored_exception(self):
        config = self.config

        config.registry.settings['pyramid_crow.ignore'] =\
            'pyramid_crow.tests.IgnoredException'

        def view(request):
            raise IgnoredException()

        config.add_view(view, name='', renderer='string')

        app = self._makeApp()

        with mock.patch.object(pyramid_crow.Client,
                               'captureException') as mock_capture:
            self.assertRaises(IgnoredException, app.get, '/')

        mock_capture.assert_not_called()

    def test_http_exception(self):
        config = self.config

        config.registry.settings['pyramid_crow.ignore'] =\
            'pyramid_crow.tests.IgnoredException'

        def view(request):
            raise httpexceptions.HTTPFound()

        config.add_view(view, name='', renderer='string')

        app = self._makeApp()

        with mock.patch.object(pyramid_crow.Client,
                               'captureException') as mock_capture:
            self.assertRaises(httpexceptions.HTTPFound, app.get, '/')

        mock_capture.assert_not_called()

    def test_capture_called(self):
        config = self.config

        def view(request):
            self.request = request
            raise ExpectedException()

        config.add_view(view, name='', renderer='string')

        app = self._makeApp()

        with mock.patch.object(
            pyramid_crow.Client, 'captureException'
        ) as mock_capture, mock.patch(
            'pyramid_crow._raven_clear_context', new=(lambda r: r)
        ):
            self.assertRaises(ExpectedException, app.get, '/')

        mock_capture.assert_called_once()
        self.assertEqual(
            self.request.raven.context['request']['method'], 'GET'
        )
        self.assertEqual(
            self.request.raven.context['request']['url'], 'http://localhost/'
        )
        self.assertEqual(
            self.request.raven.context['request']['data'], b''
        )
        self.assertEqual(
            self.request.raven.context['request']['query_string'], ''
        )
        self.assertEqual(
            self.request.raven.context['request']['headers'],
            {'Host': 'localhost:80'},
        )

    def test_capture_query_string(self):
        config = self.config

        def view(request):
            self.request = request
            raise ExpectedException()

        config.add_view(view, name='', renderer='string')

        app = self._makeApp()

        with mock.patch.object(
            pyramid_crow.Client, 'captureException'
        ) as mock_capture, mock.patch(
            'pyramid_crow._raven_clear_context', new=(lambda r: r)
        ):
            self.assertRaises(ExpectedException, app.get, '/',
                              params=(('foo', 'bar'), ('baz', 'garply'))
                              )

        mock_capture.assert_called_once()
        self.assertEqual(
            self.request.raven.context['request']['method'], 'GET'
        )
        self.assertEqual(
            self.request.raven.context['request']['url'], 'http://localhost/'
        )
        self.assertEqual(
            self.request.raven.context['request']['data'], b''
        )
        self.assertEqual(
            self.request.raven.context['request']['query_string'],
            'foo=bar&baz=garply'
        )
        self.assertEqual(
            self.request.raven.context['request']['headers'],
            {'Host': 'localhost:80'},
        )

    def test_context_empty(self):
        config = self.config

        def view(request):
            self.request = request
            raise ExpectedException()

        config.add_view(view, name='', renderer='string')

        app = self._makeApp()

        with mock.patch.object(pyramid_crow.Client,
                               'captureException') as mock_capture:
            self.assertRaises(ExpectedException, app.get, '/',
                              params=(('foo', 'bar'), ('baz', 'garply')))

        mock_capture.assert_called_once()
        self.assertFalse('request' in self.request.raven.context)

    def test_capture_body(self):
        config = self.config

        def view(request):
            self.request = request
            raise ExpectedException()

        config.add_view(view, name='', renderer='string')

        app = self._makeApp()

        with mock.patch.object(
            pyramid_crow.Client, 'captureException'
        ) as mock_capture, mock.patch(
            'pyramid_crow._raven_clear_context', new=(lambda r: r)
        ):
            self.assertRaises(ExpectedException, app.post, '/',
                              params=(('foo', 'bar'), ('baz', 'garply'))
                              )

        mock_capture.assert_called_once()
        self.assertEqual(
            self.request.raven.context['request']['method'], 'POST'
        )
        self.assertEqual(
            self.request.raven.context['request']['url'], 'http://localhost/'
        )
        self.assertEqual(
            self.request.raven.context['request']['data'], b'foo=bar&baz=garply'
        )
        self.assertEqual(
            self.request.raven.context['request']['query_string'], ''
        )
        self.assertEqual(
            self.request.raven.context['request']['headers'],
            {
                'Content-Length': '18',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Host': 'localhost:80',
            },
        )

    def test_scrub_sensitive_get(self):
        """Bad form to submit VIA get but let's not leak everywhere"""
        config = self.config

        def view(request):
            self.request = request
            raise ExpectedException()

        config.add_view(view, name='', renderer='string')

        app = self._makeApp()

        with mock.patch.object(pyramid_crow.Client,
                               'send') as mock_send:
            self.assertRaises(ExpectedException, app.get, '/',
                              params=(('password', 'ohno'),))

        sentry_data = mock_send.call_args[1]

        dumped_data = json.dumps(sentry_data)
        self.assertNotIn('ohno', dumped_data)

    def test_scrub_sensitive_post(self):
        config = self.config

        def view(request):
            self.request = request
            raise ExpectedException()

        config.add_view(view, name='', renderer='string')

        app = self._makeApp()

        with mock.patch.object(pyramid_crow.Client,
                               'send') as mock_send:
            self.assertRaises(ExpectedException, app.post, '/',
                              params=(('password', 'ohno'),))

        sentry_data = mock_send.call_args[1]

        dumped_data = json.dumps(sentry_data)
        self.assertNotIn('ohno', dumped_data)
