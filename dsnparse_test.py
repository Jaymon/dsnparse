from unittest import TestCase
import os

import dsnparse

class DsnParseTest(TestCase):
    def test_parse(self):
        tests = [
            (
                'scheme://username:password@host:1234/bar/che?option1=opt_val1&option2=opt_val2#anchor',
                {
                    'scheme': 'scheme',
                    'schemes': ['scheme'],
                    'username': 'username',
                    'password': 'password',
                    'netloc': 'username:password@host:1234',
                    'host': 'host',
                    'hostloc': 'host:1234',
                    'path': '/bar/che',
                    'paths': ['bar', 'che'],
                    'hostname': 'host',
                    'query': {'option1': 'opt_val1', 'option2': 'opt_val2'},
                    'fragment': 'anchor'
                }
            ),
            (
                'scheme://localhost',
                {
                    'scheme': 'scheme',
                    'schemes': ['scheme'],
                    'netloc': 'localhost',
                    'host': 'localhost',
                    'hostloc': 'localhost',
                    'path': '',
                    'paths': [],
                    'hostname': 'localhost',
                    'query': {}
                }
            ),
            (
                'scheme1+scheme2://username:password@host.com:9000/?opt=opt_val1&opt=opt_val2#anchor',
                {
                    'scheme': 'scheme1+scheme2',
                    'schemes': ['scheme1', 'scheme2'],
                    'username': 'username',
                    'password': 'password',
                    'netloc': 'username:password@host.com:9000',
                    'host': 'host.com',
                    'hostloc': 'host.com:9000',
                    'path': '/',
                    'paths': [],
                    'hostname': 'host.com',
                    'query': {'opt': ['opt_val1', 'opt_val2']},
                    'fragment': 'anchor'
                }
            ),
        ]

        for dsn, test_out in tests:
            r = dsnparse.parse(dsn)
            for k, v in test_out.iteritems():
                self.assertEqual(v, getattr(r, k))

        with self.assertRaises(AssertionError):
            r = dsnparse.parse('//host.com:1234')

    def test_geturl(self):
        dsn = 'scheme://username:password@host:1234/bar/che?option1=opt_val1&option2=opt_val2#anchor'
        r = dsnparse.parse(dsn)
        self.assertEqual(dsn, r.geturl())

    def test_parse_environ(self):
        os.environ['TEST_DSN'] = 'scheme://username:password@host:1234/foo'
        r = dsnparse.parse_environ('TEST_DSN')
        self.assertEqual(os.environ['TEST_DSN'], r.geturl())

    def test_unpack(self):
        dsn = 'scheme://username:password@host:1234/foo'
        dsn_test = {
            'scheme': 'scheme',
            'netloc': 'username:password@host:1234',
            'path': '/foo',
            'params': "",
            'query': {},
            'fragment': ''
        }
        scheme, netloc, path, params, query, fragment = dsnparse.parse(dsn)
        self.assertEqual('scheme', scheme)
        self.assertEqual('username:password@host:1234', netloc)
        self.assertEqual('/foo', path)
        self.assertEqual('', params)
        self.assertEqual({}, query)
        self.assertEqual('', fragment)

    def test___getitem__(self):
        dsn = 'scheme://username:password@host:1234/foo'
        r = dsnparse.parse(dsn)
        self.assertEqual('scheme', r[0])
        self.assertEqual('username:password@host:1234', r[1])
        self.assertEqual('/foo', r[2])
        self.assertEqual('', r[3])
        self.assertEqual({}, r[4])
        self.assertEqual('', r[5])

    def test_setdefault(self):
        dsn = 'scheme://username:password@host/foo'
        r = dsnparse.parse(dsn)
        self.assertEqual(None, r.port)

        r.setdefault('port', 1234)
        self.assertEqual(1234, r.port)

        r = dsnparse.parse(dsn, port=1235)
        self.assertEqual(1235, r.port)


