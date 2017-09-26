# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
from unittest import TestCase, main
import os

import dsnparse


class DsnParseTest(TestCase):
    def test_parse_memory(self):
        dsn = 'scheme.Foo://:memory:?opt=val'
        r = dsnparse.parse(dsn)
        self.assertIsNone(r.hostname)
        self.assertIsNone(r.port)
        self.assertEqual(':memory:', r.path)

    def test_parse_crazy_path(self):
        dsn = 'scheme.Foo://../../bar/che.db'
        r = dsnparse.parse(dsn)
        self.assertIsNone(r.hostname)
        self.assertEqual('../../bar/che.db', r.path)

    def test_parse_rel_path_2(self):
        dsn = 'scheme.Foo://../bar/che.db'
        r = dsnparse.parse(dsn)
        self.assertIsNone(r.hostname)
        self.assertEqual('../bar/che.db', r.path)

    def test_parse_rel_path(self):
        dsn = 'scheme.Foo://./bar/che.db'
        r = dsnparse.parse(dsn)
        self.assertIsNone(r.hostname)
        self.assertEqual('./bar/che.db', r.path)

    def test_parse_abs_path(self):
        dsn = 'scheme.Foo:///bar/che.db'
        r = dsnparse.parse(dsn)
        self.assertEqual('scheme.Foo', r.scheme)
        self.assertEqual('/bar/che.db', r.path)

    def test_parse_custom_class(self):
        class CustomParseResult(dsnparse.ParseResult):
            pass

        dsn = 'scheme://user:pass@host:1234/bar/che?option1=opt_val1#anchor'
        r = dsnparse.parse(dsn, parse_class=CustomParseResult)
        self.assertTrue(isinstance(r, CustomParseResult))

    def test_parse(self):
        tests = [
            (
                'scheme://:password@host:1234/bar/che?option1=opt_val1&option2=opt_val2#anchor',
                {
                    'scheme': 'scheme',
                    'schemes': ['scheme'],
                    'username': '',
                    'password': 'password',
                    'netloc': ':password@host:1234',
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
                'scheme://username@host:1234/bar/che?option1=opt_val1&option2=opt_val2#anchor',
                {
                    'scheme': 'scheme',
                    'schemes': ['scheme'],
                    'username': 'username',
                    'password': None,
                    'netloc': 'username@host:1234',
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
            for k, v in test_out.items():
                self.assertEqual(v, getattr(r, k))

        with self.assertRaises(ValueError):
            r = dsnparse.parse('//host.com:1234')

    def test_geturl(self):
        dsn = 'scheme://username:password@host:1234/bar/che?option1=opt_val1&option2=opt_val2#anchor'
        r = dsnparse.parse(dsn)
        self.assertEqual(dsn, r.geturl())

    def test_parse_environ(self):
        os.environ['ENVIRON_DSN'] = 'scheme://username:password@host:1234/foo'
        r = dsnparse.parse_environ('ENVIRON_DSN')
        self.assertEqual(os.environ['ENVIRON_DSN'], r.geturl())

    def test_parse_environs(self):
        os.environ['ENVIRONS_DSN_1'] = 'scheme://username:password@host:1234/foo'
        os.environ['ENVIRONS_DSN_2'] = 'scheme://username:password@host:1234/bar'
        os.environ['ENVIRONS_DSN_3'] = 'scheme://username:password@host:1234/che'
        rs = dsnparse.parse_environs('ENVIRONS_DSN')
        self.assertEqual(3, len(rs))
        for x in range(1, 4):
            self.assertEqual(os.environ['ENVIRONS_DSN_{x}'.format(x=x)], rs[x - 1].geturl())

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


if __name__ == '__main__':
    main()

