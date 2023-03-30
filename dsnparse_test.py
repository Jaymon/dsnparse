# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import sys
import os
from urllib.parse import unquote, quote
from unittest import TestCase, main

import dsnparse
from dsnparse import (
    ConnectionString,
    ConnectionURI,
    ParseResult,
)


class ConnectionStringTest(TestCase):
    def test_string(self):
        tests = [
            (
                "value='foo \\\' bar' " + 'value2="bar\\\"che"',
                {
                    'value': 'foo \\\' bar',
                    'value2': "bar\\\"che",
                }
            ),
            (
                "host=localhost port=5432 dbname=mydb connect_timeout=10",
                {
                    'host': "localhost",
                    'port': 5432,
                    'dbname': "mydb",
                    'connect_timeout': 10
                }
            ),
            (
                "host = localhost port= 5432 dbname =mydb",
                {
                    'host': "localhost",
                    'port': 5432,
                    'dbname': "mydb",
                }
            ),
            (
                "value = 'foo bar'",
                {
                    'value': "foo bar",
                }
            ),
        ]

        for dsn, test_out in tests:
            r = ConnectionString(dsn)
            for k, v in test_out.items():
                self.assertEqual(v, r[k], dsn)


class ConnectionURITest(TestCase):
    def test_parse_scheme(self):
        r = ConnectionURI()
        parts = r.parse_scheme("foo:")
        self.assertEqual("foo", parts[0])
        self.assertEqual("", parts[1])

        parts = r.parse_scheme("foo://authority/")
        self.assertEqual("foo", parts[0])
        self.assertEqual("//authority/", parts[1])

        parts = r.parse_scheme("foo")
        self.assertEqual("", parts[0])
        self.assertEqual("foo", parts[1])

    def test_parse_authority(self):
        r = ConnectionURI()
        parts = r.parse_authority("//authority/")
        self.assertEqual("authority", parts[0])
        self.assertEqual("/", parts[1])

        parts = r.parse_authority("//authority/path/")
        self.assertEqual("authority", parts[0])
        self.assertEqual("/path/", parts[1])

    def test_parse_userinfo(self):
        r = ConnectionURI()

        parts = r.parse_userinfo("username:password@")
        self.assertEqual("username", parts[0])
        self.assertEqual("password", parts[1])
        self.assertEqual("", parts[2])

        parts = r.parse_userinfo("localhost:5000")
        self.assertEqual(None, parts[0])
        self.assertEqual(None, parts[1])
        self.assertEqual("localhost:5000", parts[2])

        username = "foobar@example.tld"
        password = "?:@+"
        parts = r.parse_userinfo(f"{quote(username)}:{quote(password)}@")
        self.assertEqual(username, parts[0])
        self.assertEqual(password, parts[1])

        parts = r.parse_userinfo(":password@")
        self.assertEqual("", parts[0])
        self.assertEqual("password", parts[1])

        parts = r.parse_userinfo("username:@")
        self.assertEqual("username", parts[0])
        self.assertEqual("", parts[1])

        parts = r.parse_userinfo("username@host:1234")
        self.assertEqual("username", parts[0])
        self.assertEqual("", parts[1])

    def test_parse_hosts(self):
        r = ConnectionURI()

        parts = r.parse_hosts("localhost:5001,example:5002,192.168.0.111:5003")
        self.assertEqual(3, len(parts))
        self.assertEqual("192.168.0.111", parts[2][0])
        self.assertEqual(5002, parts[1][1])

        parts = r.parse_hosts("localhost:5000")
        self.assertEqual(1, len(parts))
        self.assertEqual("localhost", parts[0][0])
        self.assertEqual(5000, parts[0][1])

        parts = r.parse_hosts("localhost")
        self.assertEqual(1, len(parts))
        self.assertEqual("localhost", parts[0][0])
        self.assertEqual(None, parts[0][1])

    def test_parse_hostloc(self):
        r = ConnectionURI()
        hostloc = 'host:1234'
        parts = r.parse_hostloc(hostloc)
        self.assertEqual(2, len(parts))
        self.assertEqual("host", parts[0])
        self.assertEqual(1234, parts[1])

    def test_uri(self):
        dsn = "foo://username:password@hostname:6000/p/a/t/h?query=value#anchor"

        r = ConnectionURI(dsn)

    def test_parse_memory(self):
        dsn = 'scheme.Foo://:memory:?opt=val'
        r = ConnectionURI(dsn)
        self.assertIsNone(r["port"])
        self.assertEqual(':memory:', r["hostname"])

        dsn = 'scheme.Foo::memory:?opt=val'
        r = ConnectionURI(dsn)
        self.assertEqual(':memory:', r["path"])

    def test_parse_crazy_path(self):
        dsn = 'scheme.Foo://../../bar/che.db'
        r = ConnectionURI(dsn)
        self.assertIsNone(r.get("hostname", None))
        self.assertEqual('../../bar/che.db', r["path"])

    def test_parse_rel_path_1(self):
        dsn = 'scheme.Foo://./bar/che.db'
        r = ConnectionURI(dsn)
        self.assertIsNone(r.get("hostname", None))
        self.assertEqual('./bar/che.db', r.path)

    def test_parse_rel_path_2(self):
        dsn = 'scheme.Foo://../bar/che.db'
        r = ConnectionURI(dsn)
        self.assertIsNone(r.get("hostname", None))
        self.assertEqual('../bar/che.db', r.path)

    def test_parse_abs_path(self):
        dsn = 'scheme.Foo:///bar/che.db'
        r = ConnectionURI(dsn)
        self.assertEqual('scheme.Foo', r.scheme)
        self.assertEqual('/bar/che.db', r.path)

    def test_sqlite_examples(self):
        """
        https://www.sqlite.org/c3ref/open.html#urifilenameexamples
        """
        dsn = "file:/home/fred/data.db?vfs=unix-dotfile"
        r = ConnectionURI(dsn)
        self.assertEqual("file", r.scheme)
        self.assertEqual("/home/fred/data.db", r.path)

        dsn = "file:data.db?mode=readonly"
        r = ConnectionURI(dsn)
        self.assertEqual("file", r.scheme)
        self.assertEqual("data.db", r.path)
        self.assertEqual("readonly", r.query_params["mode"])

        dsn = "file:data.db?mode=ro&cache=private"
        r = ConnectionURI(dsn)
        self.assertEqual("file", r.scheme)
        self.assertEqual("data.db", r.path)
        self.assertTrue("mode" in r.query_params)
        self.assertEqual("private", r.query_params["cache"])

        dsn = "file:///C:/Documents%20and%20Settings/fred/Desktop/data.db"
        r = ConnectionURI(dsn)
        self.assertEqual("file", r.scheme)
        self.assertEqual("/C:/Documents%20and%20Settings/fred/Desktop/data.db", r.path)

        dsn = "file:data.db"
        r = ConnectionURI(dsn)
        self.assertEqual("file", r.scheme)
        self.assertEqual("data.db", r.path)

        dsn = "file:/home/fred/data.db"
        r = ConnectionURI(dsn)
        self.assertEqual("file", r.scheme)
        self.assertEqual("/home/fred/data.db", r.path)

        dsn = "file:///home/fred/data.db"
        r = ConnectionURI(dsn)
        self.assertEqual("file", r.scheme)
        self.assertEqual("/home/fred/data.db", r.path)

        dsn = "file://localhost/home/fred/data.db"
        r = ConnectionURI(dsn)
        self.assertEqual("file", r.scheme)
        self.assertEqual("localhost", r.hostname)
        self.assertEqual("/home/fred/data.db", r.path)


class ParseResultTest(TestCase):
    def test_database(self):
        dsn = "sqlite:///the/path"
        r = ParseResult(dsn)
        self.assertEqual("/the/path", r.database)
        self.assertEqual("/the/path", r.dbname)

        dsn = "postgresql://user:pass@host:1234/dbname"
        r = ParseResult(dsn)
        self.assertEqual("dbname", r.database)
        self.assertEqual("dbname", r.dbname)

        dsn = "postgresql://user:pass@host:1234/dbname/"
        r = ParseResult(dsn)
        self.assertEqual("dbname", r.dbname)

    def test_parse(self):
        tests = [
            (
                'scheme://:password@host:1234/bar/che?option1=opt_val1&option2=opt_val2#anchor',
                {
                    'scheme': 'scheme',
                    'schemes': ['scheme'],
                    'username': None,
                    'password': 'password',
                    'netloc': ':password@host:1234',
                    'host': 'host',
                    'hostloc': 'host:1234',
                    'path': '/bar/che',
                    'paths': ['bar', 'che'],
                    'hostname': 'host',
                    'query_params': {'option1': 'opt_val1', 'option2': 'opt_val2'},
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
                    'query_params': {'option1': 'opt_val1', 'option2': 'opt_val2'},
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
                    'query_params': {'option1': 'opt_val1', 'option2': 'opt_val2'},
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
                    'query_params': {}
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
                    'query_params': {'opt': ['opt_val1', 'opt_val2']},
                    'fragment': 'anchor'
                }
            ),
        ]

        for dsn, test_out in tests:
            r = dsnparse.parse(dsn)
            for k, v in test_out.items():
                self.assertEqual(v, getattr(r, k), f"{k} in {dsn}")

        with self.assertRaises(ValueError):
            r = dsnparse.parse('//host.com:1234')

    def test_geturl(self):
        dsn = 'scheme://username:password@host:1234/bar/che?option1=opt_val1&option2=opt_val2#anchor'
        r = dsnparse.parse(dsn)
        self.assertEqual(dsn, r.geturl())

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
        self.assertEqual("scheme", scheme)
        self.assertEqual("username:password@host:1234", netloc)
        self.assertEqual("/foo", path)
        self.assertEqual("", params)
        self.assertEqual("", query)
        self.assertEqual("", fragment)

    def test___getitem__(self):
        dsn = "scheme://username:password@host:1234/foo"
        r = dsnparse.parse(dsn)
        self.assertEqual("scheme", r[0])
        self.assertEqual("username:password@host:1234", r[1])
        self.assertEqual("/foo", r[2])
        self.assertEqual("", r[3])
        self.assertEqual("", r[4])
        self.assertEqual("", r[5])

    def test_setdefault(self):
        dsn = 'scheme://username:password@host/foo'
        r = dsnparse.parse(dsn)
        self.assertEqual(None, r.port)

        r.setdefault('port', 1234)
        self.assertEqual(1234, r.port)

        r = dsnparse.parse(dsn, port=1235)
        self.assertEqual(1235, r.port)

    def test_url_encoding(self):
        dsn = "postgresql://%2Fvar%2Flib%2Fpostgresql/dbname"
        r = dsnparse.parse(dsn)
        self.assertFalse("%2" in r.hostname)
        self.assertTrue("%2" in r.netloc)

    def test_options_define(self):
        dsn = "postgresql:///dbname?hostname=/var/lib/postgresql"
        r = dsnparse.parse(dsn)
        self.assertEqual("/var/lib/postgresql", r.hostname)
        self.assertEqual("dbname", r.database)

    def test_username_password(self):
        username = "foo"
        password = "bar+che/baz"
        dsn = f"scheme://{username}:{quote(password, safe='')}@"
        r = dsnparse.parse(dsn)
        self.assertEqual("foo", r.username)
        self.assertEqual("bar+che/baz", r.password)

        dsn = "scheme://example.com/?username=foo2&password=che-baz"
        r = dsnparse.parse(dsn)
        self.assertEqual("foo2", r.username)
        self.assertEqual("che-baz", r.password)

        dsn = "scheme://foo3:bar3@example.com/?username=foo3&password=bar3"
        with self.assertRaises(ValueError):
            r = dsnparse.parse(dsn)

    def test_postgres_example(self):
        """
        https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING
        """
        dsn = "host=localhost port=5432 dbname=mydb connect_timeout=10"
        r = dsnparse.parse(dsn)
        self.assertEqual("localhost", r.hostname)
        self.assertEqual("localhost", r.host)
        self.assertEqual(5432, r.port)
        self.assertEqual("mydb", r.dbname)
        self.assertEqual("mydb", r.database)
        self.assertEqual(10, r.query_params["connect_timeout"])


class DsnParseTest(TestCase):
    def test_parse_custom_class(self):
        class CustomParseResult(dsnparse.ParseResult):
            pass

        dsn = 'scheme://user:pass@host:1234/bar/che?option1=opt_val1#anchor'
        r = dsnparse.parse(dsn, parse_class=CustomParseResult)
        self.assertTrue(isinstance(r, CustomParseResult))

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


if __name__ == '__main__':
    main()

