from __future__ import unicode_literals

import time
import warnings
from datetime import datetime, timedelta

from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest, LimitedStream
from django.http import HttpRequest, HttpResponse, parse_cookie, build_request_repr, UnreadablePostError
from django.test.utils import str_prefix
from django.utils import unittest
from django.utils.http import cookie_date
from django.utils.six import StringIO
from django.utils.timezone import utc


class RequestsTests(unittest.TestCase):
    def test_httprequest(self):
        request = HttpRequest()
        self.assertEqual(request.GET.keys(), [])
        self.assertEqual(request.POST.keys(), [])
        self.assertEqual(request.COOKIES.keys(), [])
        self.assertEqual(request.META.keys(), [])

    def test_httprequest_repr(self):
        request = HttpRequest()
        request.path = '/somepath/'
        request.GET = {'get-key': 'get-value'}
        request.POST = {'post-key': 'post-value'}
        request.COOKIES = {'post-key': 'post-value'}
        request.META = {'post-key': 'post-value'}
        self.assertEqual(repr(request), str_prefix("<HttpRequest\npath:/somepath/,\nGET:{%(_)s'get-key': %(_)s'get-value'},\nPOST:{%(_)s'post-key': %(_)s'post-value'},\nCOOKIES:{%(_)s'post-key': %(_)s'post-value'},\nMETA:{%(_)s'post-key': %(_)s'post-value'}>"))
        self.assertEqual(build_request_repr(request), repr(request))
        self.assertEqual(build_request_repr(request, path_override='/otherpath/', GET_override={'a': 'b'}, POST_override={'c': 'd'}, COOKIES_override={'e': 'f'}, META_override={'g': 'h'}),
                         str_prefix("<HttpRequest\npath:/otherpath/,\nGET:{%(_)s'a': %(_)s'b'},\nPOST:{%(_)s'c': %(_)s'd'},\nCOOKIES:{%(_)s'e': %(_)s'f'},\nMETA:{%(_)s'g': %(_)s'h'}>"))

    def test_wsgirequest(self):
        request = WSGIRequest({'PATH_INFO': 'bogus', 'REQUEST_METHOD': 'bogus', 'wsgi.input': StringIO('')})
        self.assertEqual(request.GET.keys(), [])
        self.assertEqual(request.POST.keys(), [])
        self.assertEqual(request.COOKIES.keys(), [])
        self.assertEqual(set(request.META.keys()), set(['PATH_INFO', 'REQUEST_METHOD', 'SCRIPT_NAME', 'wsgi.input']))
        self.assertEqual(request.META['PATH_INFO'], 'bogus')
        self.assertEqual(request.META['REQUEST_METHOD'], 'bogus')
        self.assertEqual(request.META['SCRIPT_NAME'], '')

    def test_wsgirequest_repr(self):
        request = WSGIRequest({'PATH_INFO': '/somepath/', 'REQUEST_METHOD': 'get', 'wsgi.input': StringIO('')})
        request.GET = {'get-key': 'get-value'}
        request.POST = {'post-key': 'post-value'}
        request.COOKIES = {'post-key': 'post-value'}
        request.META = {'post-key': 'post-value'}
        self.assertEqual(repr(request), str_prefix("<WSGIRequest\npath:/somepath/,\nGET:{%(_)s'get-key': %(_)s'get-value'},\nPOST:{%(_)s'post-key': %(_)s'post-value'},\nCOOKIES:{%(_)s'post-key': %(_)s'post-value'},\nMETA:{%(_)s'post-key': %(_)s'post-value'}>"))
        self.assertEqual(build_request_repr(request), repr(request))
        self.assertEqual(build_request_repr(request, path_override='/otherpath/', GET_override={'a': 'b'}, POST_override={'c': 'd'}, COOKIES_override={'e': 'f'}, META_override={'g': 'h'}),
                         str_prefix("<WSGIRequest\npath:/otherpath/,\nGET:{%(_)s'a': %(_)s'b'},\nPOST:{%(_)s'c': %(_)s'd'},\nCOOKIES:{%(_)s'e': %(_)s'f'},\nMETA:{%(_)s'g': %(_)s'h'}>"))

    def test_parse_cookie(self):
        self.assertEqual(parse_cookie('invalid:key=true'), {})

    def test_httprequest_location(self):
        request = HttpRequest()
        self.assertEqual(request.build_absolute_uri(location="https://www.example.com/asdf"),
            'https://www.example.com/asdf')

        request.get_host = lambda: 'www.example.com'
        request.path = ''
        self.assertEqual(request.build_absolute_uri(location="/path/with:colons"),
            'http://www.example.com/path/with:colons')

    def test_http_get_host(self):
        old_USE_X_FORWARDED_HOST = settings.USE_X_FORWARDED_HOST
        try:
            settings.USE_X_FORWARDED_HOST = False

            # Check if X_FORWARDED_HOST is provided.
            request = HttpRequest()
            request.META = {
                'HTTP_X_FORWARDED_HOST': 'forward.com',
                'HTTP_HOST': 'example.com',
                'SERVER_NAME': 'internal.com',
                'SERVER_PORT': 80,
            }
            # X_FORWARDED_HOST is ignored.
            self.assertEqual(request.get_host(), 'example.com')

            # Check if X_FORWARDED_HOST isn't provided.
            request = HttpRequest()
            request.META = {
                'HTTP_HOST': 'example.com',
                'SERVER_NAME': 'internal.com',
                'SERVER_PORT': 80,
            }
            self.assertEqual(request.get_host(), 'example.com')

            # Check if HTTP_HOST isn't provided.
            request = HttpRequest()
            request.META = {
                'SERVER_NAME': 'internal.com',
                'SERVER_PORT': 80,
            }
            self.assertEqual(request.get_host(), 'internal.com')

            # Check if HTTP_HOST isn't provided, and we're on a nonstandard port
            request = HttpRequest()
            request.META = {
                'SERVER_NAME': 'internal.com',
                'SERVER_PORT': 8042,
            }
            self.assertEqual(request.get_host(), 'internal.com:8042')

        finally:
            settings.USE_X_FORWARDED_HOST = old_USE_X_FORWARDED_HOST

    def test_http_get_host_with_x_forwarded_host(self):
        old_USE_X_FORWARDED_HOST = settings.USE_X_FORWARDED_HOST
        try:
            settings.USE_X_FORWARDED_HOST = True

            # Check if X_FORWARDED_HOST is provided.
            request = HttpRequest()
            request.META = {
                'HTTP_X_FORWARDED_HOST': 'forward.com',
                'HTTP_HOST': 'example.com',
                'SERVER_NAME': 'internal.com',
                'SERVER_PORT': 80,
            }
            # X_FORWARDED_HOST is obeyed.
            self.assertEqual(request.get_host(), 'forward.com')

            # Check if X_FORWARDED_HOST isn't provided.
            request = HttpRequest()
            request.META = {
                'HTTP_HOST': 'example.com',
                'SERVER_NAME': 'internal.com',
                'SERVER_PORT': 80,
            }
            self.assertEqual(request.get_host(), 'example.com')

            # Check if HTTP_HOST isn't provided.
            request = HttpRequest()
            request.META = {
                'SERVER_NAME': 'internal.com',
                'SERVER_PORT': 80,
            }
            self.assertEqual(request.get_host(), 'internal.com')

            # Check if HTTP_HOST isn't provided, and we're on a nonstandard port
            request = HttpRequest()
            request.META = {
                'SERVER_NAME': 'internal.com',
                'SERVER_PORT': 8042,
            }
            self.assertEqual(request.get_host(), 'internal.com:8042')

        finally:
            settings.USE_X_FORWARDED_HOST = old_USE_X_FORWARDED_HOST

    def test_near_expiration(self):
        "Cookie will expire when an near expiration time is provided"
        response = HttpResponse()
        # There is a timing weakness in this test; The
        # expected result for max-age requires that there be
        # a very slight difference between the evaluated expiration
        # time, and the time evaluated in set_cookie(). If this
        # difference doesn't exist, the cookie time will be
        # 1 second larger. To avoid the problem, put in a quick sleep,
        # which guarantees that there will be a time difference.
        expires = datetime.utcnow() + timedelta(seconds=10)
        time.sleep(0.001)
        response.set_cookie('datetime', expires=expires)
        datetime_cookie = response.cookies['datetime']
        self.assertEqual(datetime_cookie['max-age'], 10)

    def test_aware_expiration(self):
        "Cookie accepts an aware datetime as expiration time"
        response = HttpResponse()
        expires = (datetime.utcnow() + timedelta(seconds=10)).replace(tzinfo=utc)
        time.sleep(0.001)
        response.set_cookie('datetime', expires=expires)
        datetime_cookie = response.cookies['datetime']
        self.assertEqual(datetime_cookie['max-age'], 10)

    def test_far_expiration(self):
        "Cookie will expire when an distant expiration time is provided"
        response = HttpResponse()
        response.set_cookie('datetime', expires=datetime(2028, 1, 1, 4, 5, 6))
        datetime_cookie = response.cookies['datetime']
        self.assertEqual(datetime_cookie['expires'], 'Sat, 01-Jan-2028 04:05:06 GMT')

    def test_max_age_expiration(self):
        "Cookie will expire if max_age is provided"
        response = HttpResponse()
        response.set_cookie('max_age', max_age=10)
        max_age_cookie = response.cookies['max_age']
        self.assertEqual(max_age_cookie['max-age'], 10)
        self.assertEqual(max_age_cookie['expires'], cookie_date(time.time()+10))

    def test_httponly_cookie(self):
        response = HttpResponse()
        response.set_cookie('example', httponly=True)
        example_cookie = response.cookies['example']
        # A compat cookie may be in use -- check that it has worked
        # both as an output string, and using the cookie attributes
        self.assertTrue('; httponly' in str(example_cookie))
        self.assertTrue(example_cookie['httponly'])

    def test_limited_stream(self):
        # Read all of a limited stream
        stream = LimitedStream(StringIO(b'test'), 2)
        self.assertEqual(stream.read(), b'te')
        # Reading again returns nothing.
        self.assertEqual(stream.read(), b'')

        # Read a number of characters greater than the stream has to offer
        stream = LimitedStream(StringIO(b'test'), 2)
        self.assertEqual(stream.read(5), b'te')
        # Reading again returns nothing.
        self.assertEqual(stream.readline(5), b'')

        # Read sequentially from a stream
        stream = LimitedStream(StringIO(b'12345678'), 8)
        self.assertEqual(stream.read(5), b'12345')
        self.assertEqual(stream.read(5), b'678')
        # Reading again returns nothing.
        self.assertEqual(stream.readline(5), b'')

        # Read lines from a stream
        stream = LimitedStream(StringIO(b'1234\n5678\nabcd\nefgh\nijkl'), 24)
        # Read a full line, unconditionally
        self.assertEqual(stream.readline(), b'1234\n')
        # Read a number of characters less than a line
        self.assertEqual(stream.readline(2), b'56')
        # Read the rest of the partial line
        self.assertEqual(stream.readline(), b'78\n')
        # Read a full line, with a character limit greater than the line length
        self.assertEqual(stream.readline(6), b'abcd\n')
        # Read the next line, deliberately terminated at the line end
        self.assertEqual(stream.readline(4), b'efgh')
        # Read the next line... just the line end
        self.assertEqual(stream.readline(), b'\n')
        # Read everything else.
        self.assertEqual(stream.readline(), b'ijkl')

        # Regression for #15018
        # If a stream contains a newline, but the provided length
        # is less than the number of provided characters, the newline
        # doesn't reset the available character count
        stream = LimitedStream(StringIO(b'1234\nabcdef'), 9)
        self.assertEqual(stream.readline(10), b'1234\n')
        self.assertEqual(stream.readline(3), b'abc')
        # Now expire the available characters
        self.assertEqual(stream.readline(3), b'd')
        # Reading again returns nothing.
        self.assertEqual(stream.readline(2), b'')

        # Same test, but with read, not readline.
        stream = LimitedStream(StringIO(b'1234\nabcdef'), 9)
        self.assertEqual(stream.read(6), b'1234\na')
        self.assertEqual(stream.read(2), b'bc')
        self.assertEqual(stream.read(2), b'd')
        self.assertEqual(stream.read(2), b'')
        self.assertEqual(stream.read(), b'')

    def test_stream(self):
        payload = b'name=value'
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': StringIO(payload)})
        self.assertEqual(request.read(), b'name=value')

    def test_read_after_value(self):
        """
        Reading from request is allowed after accessing request contents as
        POST or body.
        """
        payload = b'name=value'
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': StringIO(payload)})
        self.assertEqual(request.POST, {'name': ['value']})
        self.assertEqual(request.body, b'name=value')
        self.assertEqual(request.read(), b'name=value')

    def test_value_after_read(self):
        """
        Construction of POST or body is not allowed after reading
        from request.
        """
        payload = b'name=value'
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': StringIO(payload)})
        self.assertEqual(request.read(2), b'na')
        self.assertRaises(Exception, lambda: request.body)
        self.assertEqual(request.POST, {})

    def test_body_after_POST_multipart(self):
        """
        Reading body after parsing multipart is not allowed
        """
        # Because multipart is used for large amounts fo data i.e. file uploads,
        # we don't want the data held in memory twice, and we don't want to
        # silence the error by setting body = '' either.
        payload = "\r\n".join([
                '--boundary',
                'Content-Disposition: form-data; name="name"',
                '',
                'value',
                '--boundary--'
                '']).encode('utf-8')
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_TYPE': 'multipart/form-data; boundary=boundary',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': StringIO(payload)})
        self.assertEqual(request.POST, {'name': ['value']})
        self.assertRaises(Exception, lambda: request.body)

    def test_POST_multipart_with_content_length_zero(self):
        """
        Multipart POST requests with Content-Length >= 0 are valid and need to be handled.
        """
        # According to:
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.13
        # Every request.POST with Content-Length >= 0 is a valid request,
        # this test ensures that we handle Content-Length == 0.
        payload = "\r\n".join([
                '--boundary',
                'Content-Disposition: form-data; name="name"',
                '',
                'value',
                '--boundary--'
                '']).encode('utf-8')
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_TYPE': 'multipart/form-data; boundary=boundary',
                               'CONTENT_LENGTH': 0,
                               'wsgi.input': StringIO(payload)})
        self.assertEqual(request.POST, {})

    def test_read_by_lines(self):
        payload = b'name=value'
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': StringIO(payload)})
        self.assertEqual(list(request), [b'name=value'])

    def test_POST_after_body_read(self):
        """
        POST should be populated even if body is read first
        """
        payload = b'name=value'
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': StringIO(payload)})
        raw_data = request.body
        self.assertEqual(request.POST, {'name': ['value']})

    def test_POST_after_body_read_and_stream_read(self):
        """
        POST should be populated even if body is read first, and then
        the stream is read second.
        """
        payload = b'name=value'
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': StringIO(payload)})
        raw_data = request.body
        self.assertEqual(request.read(1), b'n')
        self.assertEqual(request.POST, {'name': ['value']})

    def test_POST_after_body_read_and_stream_read_multipart(self):
        """
        POST should be populated even if body is read first, and then
        the stream is read second. Using multipart/form-data instead of urlencoded.
        """
        payload = "\r\n".join([
                '--boundary',
                'Content-Disposition: form-data; name="name"',
                '',
                'value',
                '--boundary--'
                '']).encode('utf-8')
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_TYPE': 'multipart/form-data; boundary=boundary',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': StringIO(payload)})
        raw_data = request.body
        # Consume enough data to mess up the parsing:
        self.assertEqual(request.read(13), b'--boundary\r\nC')
        self.assertEqual(request.POST, {'name': ['value']})

    def test_raw_post_data_returns_body(self):
        """
        HttpRequest.raw_post_body should be the same as HttpRequest.body
        """
        payload = b'Hello There!'
        request = WSGIRequest({
            'REQUEST_METHOD': 'POST',
            'CONTENT_LENGTH': len(payload),
            'wsgi.input': StringIO(payload)
        })

        with warnings.catch_warnings(record=True):
            self.assertEqual(request.body, request.raw_post_data)

    def test_POST_connection_error(self):
        """
        If wsgi.input.read() raises an exception while trying to read() the
        POST, the exception should be identifiable (not a generic IOError).
        """
        class ExplodingStringIO(StringIO):
            def read(self, len=0):
                raise IOError("kaboom!")

        payload = b'name=value'
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': ExplodingStringIO(payload)})

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with self.assertRaises(UnreadablePostError):
                request.raw_post_data
            self.assertEqual(len(w), 1)
