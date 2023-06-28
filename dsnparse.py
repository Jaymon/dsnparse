# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import urllib.parse as urlparse
from urllib.parse import unquote, quote
import re
import os
import logging


__version__ = '0.2.1'


logger = logging.getLogger(__name__)


class ConnectionString(dict):
    """A connection string is a name=value string

    :Example:
        dsn = "name=value name2 = 'value 2'"
        c = ConnectionString(dsn)
        print(c.name) # value
        print(c.name2) # value 2

    https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING
        In the keyword/value format, each parameter setting is in the form keyword = value,
        with space(s) between settings. Spaces around a setting's equal sign are optional.
        To write an empty value, or a value containing spaces, surround it with single
        quotes, for example keyword = 'a value'. Single quotes and backslashes within
        a value must be escaped with a backslash, i.e., \' and \\.
    """
    @classmethod
    def verify(cls, dsn):
        if re.match(r"^[a-z_][a-z0-9_-]*\s*=\s*\S", dsn, flags=re.I):
            return True
        return False

    def __init__(self, dsn=""):
        d = self.parse_dsn(dsn)
        d.setdefault("query_params", {})
        super().__init__(d)

    def __getattr__(self, k):
        try:
            return self.__getitem__(k)

        except KeyError as e:
            raise AttributeError(k) from e

    def parse_dsn(self, dsn):
        self.dsn = dsn
        return self.parse(dsn) if dsn else {}

    def parse(self, dsn):
        d = {}
        chindex = 0

        while chindex < len(dsn):
            # consume until space or =
            try:
                name = ""
                while re.match(r"[^\s=]", dsn[chindex]):
                    name += dsn[chindex]
                    chindex += 1

                # move passed spaces and =
                while re.match(r"[\s=]", dsn[chindex]):
                    chindex += 1

                # Gather value
                value = ""
                if dsn[chindex] == "\"" or dsn[chindex] == "'":
                    # value is an enclosed string, so go until we find the other quote
                    quote = dsn[chindex]
                    chindex += 1
                    while (dsn[chindex] != quote) or (dsn[chindex - 1] == "\\"):
                        value += dsn[chindex]
                        chindex += 1

                    chindex += 1

                else:
                    # value isn't quoted so just go until we hit a space
                    while re.match(r"\S", dsn[chindex]):
                        value += dsn[chindex]
                        chindex += 1

                # find the start of the next assignment
                while re.match(r"\s", dsn[chindex]):
                    chindex += 1

            except IndexError:
                # ignore running out characters
                pass

            finally:
                d[name] = value

        return self.normalize_values(d)

    def normalize_values(self, d):
        """Since values in a DSN are strings this attempts to coerce the values
        to their actual types

        :param d: dict[str, str], the values that have been parsed from the DSN
        :returns: dict[str, Any], the values with their types coerced
        """
        if not d: return d

        for k, v in d.items():
            if isinstance(v, str):
                if re.match(r"^\d+\.\d+$", v):
                    d[k] = float(v)

                elif re.match(r"^\d+$", v):
                    d[k] = int(v)

                elif re.match(r"^true$", v, flags=re.I):
                    d[k] = True

                elif re.match(r"^false$", v, flags=re.I):
                    d[k] = False

        return d


class ConnectionURI(ConnectionString):
    """Parses a traditional connection URI/DSN that is formatted mostly according 
    to rfc3986 syntax

    rfc3986 section 3:
         foo://example.com:8042/over/there?name=ferret#nose
         \_/   \______________/\_________/ \_________/ \__/
          |           |            |            |        |
       scheme     authority       path        query   fragment
          |   _____________________|__
         / \ /                        \
         urn:example:animal:ferret:nose

    * https://www.ietf.org/rfc/rfc3986.txt
    * superseded by rfc3986: https://www.ietf.org/rfc/rfc2396.txt
    * postgres connection strings: 
        https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING
    * SQLite connection strings:
        https://www.sqlite.org/uri.html
    """
    @classmethod
    def verify(cls, dsn):
        if re.match(r"^[^/]+:", dsn):
            return True
        return False

    def parse_scheme(self, dsn):
        """
        rfc3986 section 3.1:
            Scheme names consist of a sequence of characters beginning with a
            letter and followed by any combination of letters, digits, plus
            ("+"), period ("."), or hyphen ("-").
        """
        scheme = ""
        first_colon = dsn.find(":")
        if first_colon >= 0:
            scheme = unquote(dsn[0:first_colon])
            dsn = dsn[first_colon+1:]
            logger.debug(f"Parsed scheme {scheme}")

        return scheme, dsn

    def parse_authority(self, dsn):
        """
        rfc3986 section 3.2:
            The authority component is preceded by a double slash ("//") and is
            terminated by the next slash ("/"), question mark ("?"), or number
            sign ("#") character, or by the end of the URI.
        """
        authority = ""
        sentinal = "//"
        if dsn.startswith(sentinal):
            if not re.match(r"^\.+/", dsn[len(sentinal):]):
                for ch in dsn[len(sentinal):]:
                    if ch in set(["/", "?", "#"]):
                        break

                    authority += ch

            dsn = dsn[len(authority) + len(sentinal):]
            logger.debug(f"Parsed authority with {len(authority)} characters")

        return authority, dsn

    def parse_userinfo(self, authority):
        """Parse the username:password@ from the authority

        any special characters in the username or password should be urlescaped,
        you can do this with the urllib.parse.quote function. 

        :Example:
            password = quote("foo@/:bar", safe="") # foo%40%2F%3Abar

        rfc3986 section 3.2.1:
            The user information, if present, is followed by a
            commercial at-sign ("@") that delimits it from the host.
        """
        username = password = None
        parts = authority.split("@", maxsplit=1)
        if len(parts) > 1:
            username = password = ""
            userinfo = parts[0].split(":", maxsplit=1)
            if userinfo[0]:
                username = unquote(userinfo[0])
                logger.debug(f"Parsed username {username}")

            if len(userinfo) > 1:
                if userinfo[1]:
                    password = unquote(userinfo[1])
                    logger.debug(f"Parsed password with {len(password)} characters")

            authority = parts[1]

        return username, password, authority

    def parse_hosts(self, authority):
        """Parse the hosts from the host portion of the authority string

        This deviates from the official spec by allowing multiple hosts to be
        separated by a comma:

        https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING
            In the connection URI format, you can list multiple host:port pairs
            separated by commas in the host component of the URI

        rfc3986 section 3.2.2:
            The host subcomponent of authority is identified by an IP literal
            encapsulated within square brackets, an IPv4 address in dotted-
            decimal form, or a registered name
        """
        hosts = []
        for hostloc in authority.split(","):
            hostname, port = self.parse_hostloc(hostloc)
            logger.debug(f"Parsed host {hostname} with port {port}")
            if hostname or port:
                hosts.append((hostname, port))
        return hosts

    def parse_hostloc(self, hostloc):
        """Separate hostname from port"""
        port = None
        if re.search(r":\d+$", hostloc):
            parts = hostloc.split(":")
            hostname = unquote(parts[0])

            if len(parts) > 1:
                port = int(parts[1])

        else:
            hostname = unquote(hostloc)

        return hostname, port

    def parse_path(self, dsn):
        """
        rfc3986 section 3.3:
            The path is terminated by the first question mark ("?") or number sign
            ("#") character, or by the end of the URI.
        """
        path = ""
        for ch in dsn:
            if ch in set(["?", "#"]):
                break

            path += ch

        if path:
            dsn = dsn[len(path):]
            logger.debug(f"Parsed path {path}")

        return path, dsn

    def parse_query(self, dsn):
        """
        rfc3986 section 3.4:
            The query component is indicated by the first question mark ("?")
            character and terminated by a number sign ("#") character or by the
            end of the URI
        """
        query = ""
        sentinal = "?"
        if dsn.startswith(sentinal):
            for ch in dsn[len(sentinal):]:
                if ch in set(["#"]):
                    break

                query += ch

            dsn = dsn[len(query) + len(sentinal):]
            logger.debug(f"Parsed query with {len(query)} characters")

        return query, dsn

    def parse_fragment(self, dsn):
        """
        rfc3986 section 3.5:
            A fragment identifier component is indicated by the presence of a number
            sign ("#") character and terminated by the end of the URI
        """
        sentinal = "#"
        if dsn.startswith(sentinal):
            fragment = dsn[len(sentinal):]
            logger.debug(f"Parsed fragment {fragment}")
            return fragment
        return ""

    def parse_query_params(self, query):
        """parse the query into key value options

        :param query: str, the query string parsed from .parse_query
        :returns: dict[str, Any]
        """
        options = {}
        if query:
            for k, kv in urlparse.parse_qs(query, True, True).items():
                if len(kv) > 1:
                    options[k] = kv

                else:
                    options[k] = kv[0]

            logger.debug(f"Parsed query_params with {', '.join(options.keys())} keys")

        return self.normalize_values(options)

    def parse(self, dsn):
        ret = {}
        ret["scheme"], dsn = self.parse_scheme(dsn)

        authority, dsn = self.parse_authority(dsn)
        if authority:
            ret["username"], ret["password"], authority = self.parse_userinfo(authority)
            ret["hosts"] = self.parse_hosts(authority)
            if ret["hosts"]:
                ret["hostname"] = ret["hosts"][0][0]
                ret["port"] = ret["hosts"][0][1]

        ret["path"], dsn = self.parse_path(dsn)
        ret["query"], dsn = self.parse_query(dsn)
        ret["query_params"] = self.parse_query_params(ret["query"])
        ret["fragment"] = self.parse_fragment(dsn)

        return ret


class ParseResult(object):
    """
    hold the results of a parsed dsn

    this acts very similarly to the urlparse.ParseResult tuple
        * https://github.com/python/cpython/blob/3.10/Lib/urllib/parse.py
        * http://docs.python.org/2/library/urlparse.html#results-of-urlparse-and-urlsplit

    it exposes the following attributes --
        scheme
        schemes -- if your scheme has +'s in it, then this will contain a list of schemes split by +
        path
        paths -- the path segment split by /, so "/foo/bar" would be ["foo", "bar"]
        host -- same as hostname (I just like host better)
        hostname
        hostloc -- host:port
        username
        password
        netloc
        query -- the raw query string
        query_params -- a dict of the query string
        port
        fragment
        anchor -- same as fragment, just an alternative name

    :Example:
        # DSN with only a scheme
        r = ParseResult("foo:")
        r.scheme # foo

        # DSN setting username and password
        r = ParseResult("foo://user:passd@")
        r.username # user
        r.password # pass
    """
    parser_classes = [
        ConnectionString,
        ConnectionURI,
    ]

    @property
    def schemes(self):
        """the scheme, split by plus signs"""
        return self.scheme.split('+')

    @property
    def netloc(self):
        """return username:password@hostname:port"""
        s = ''
        prefix = ''
        if self.username:
            s += self.username
            prefix = '@'

        if self.password:
            s += ":{password}".format(password=self.password)
            prefix = '@'

        s += "{prefix}{hostloc}".format(prefix=prefix, hostloc=self.hostloc)
        return s

    @property
    def paths(self):
        """the path attribute split by /"""
        return list(filter(None, self.path.split('/')))

    @property
    def pathparts(self):
        return self.paths

    @property
    def parts(self):
        return self.paths

    @property
    def host(self):
        """the hostname, but I like host better"""
        return self.hostname

    @property
    def user(self):
        """alias for username to match psycopg2"""
        return self.username

    @property
    def secret(self):
        """alias for password to match postgres dsn

        https://www.postgresql.org/docs/9.2/static/libpq-connect.html#LIBPQ-CONNSTRING
        """
        return self.password

    @property
    def hostloc(self):
        """return host:port"""
        hostloc = quote(self.hostname, safe="")
        if port := self.port:
            hostloc = f"{hostloc}:{port}"

        return hostloc

    @property
    def anchor(self):
        """alternative name for the fragment"""
        return self.fragment

    @property
    def database(self):
        # sqlite uses database in its connect method https://docs.python.org/3.6/library/sqlite3.html
        if self.hostname is None:
            database = self.path

        else:
            # we have a host, which means the dsn is in the form: //hostname/database most
            # likely, so let's get rid of the slashes when setting the db
            database = self.path.strip("/")

        return database

    @property
    def dbname(self):
        """psycopg2 uses dbname

        http://initd.org/psycopg/docs/module.html#psycopg2.connect
        """
        return self.database

    def __init__(self, dsn, **kwargs):
        self.parser = self.parse(dsn)
        self.fields = self.merge(self.parser, **kwargs)
        self.configure()

    def parse(self, dsn):
        for parser_class in self.parser_classes:
            if parser_class.verify(dsn):
                if logger.isEnabledFor(logging.DEBUG):
                    logger.info(
                        f"Parsing DSN {dsn} with {parser_class.__name__} class"
                    )

                else:
                    logger.info(f"Parsing DSN with {parser_class.__name__} class")

                return parser_class(dsn)

        raise ValueError(f"Could not find a parser for {dsn}")

    def merge(self, parser, **kwargs):
        # match defaults to urlparse result
        # https://docs.python.org/3/library/urllib.parse.html#urllib.parse.urlparse
        fields = {
            "scheme": "",
            "username": None,
            "password": None,
            "hostname": None,
            "hosts": [],
            "port": None,
            "path": "",
            "params": "",
            "query": "",
            "fragment": "",
        }
        fields.update(kwargs.pop("defaults", {}))

        aliases = {
            "dbname": "path",
            "database": "path",
            "host": "hostname",
            "user": "username",
            "secret": "password",
            "anchor": "fragment",
        }

        query_params = dict(parser.get("query_params", {}))
        query_params.update(
            kwargs.pop("options",
                kwargs.pop("query_kwargs", 
                    kwargs.pop("query_params", {})
                )
            )
        )

        for k, v in parser.items():
            if k != "query_params":
                ka = aliases[k] if k in aliases else k

                if v:
                    if ka in fields:
                        fields[ka] = v

                    else:
                        query_params.setdefault(ka, v)

        for k, v in kwargs.items():
            ka = aliases[k] if k in aliases else k
            if ka in fields:
                fields[ka] = v

            else:
                query_params[ka] = v

        for k in list(query_params.keys()):
            if k in fields:
                if not fields[k]:
                    fields[k] = query_params.pop(k)

                else:
                    raise ValueError(f"{k} specified in multiple places")

        fields["query_params"] = query_params
        return fields

    def configure(self):
        """designed to be overridden in a child class"""
        pass

    def __iter__(self):
        mapping = ['scheme', 'netloc', 'path', 'params', 'query', 'fragment']
        for k in mapping:
            yield getattr(self, k, '')

    def __getitem__(self, index):
        if isinstance(index, int):
            mapping = {
                0: 'scheme',
                1: 'netloc',
                2: 'path',
                3: 'params',
                4: 'query',
                5: 'fragment',
            }

            return getattr(self, mapping[index], None)

        else:
            return getattr(self, index)

    def __getattr__(self, k):
        try:
            return self.fields[k]

        except KeyError as e:
            raise AttributeError(k) from e

    def setdefault(self, key, val):
        """set a default value for key

        this is different than dict's setdefault because it will set default either
        if the key doesn't exist, or if the value at the key evaluates to False, so
        an empty string or a None value will also be updated.

        We do this because the parser usually sets things that weren't in the DSN
        to None or "", and we want to make sure we update those correctly

        :param key: string, the attribute to update
        :param val: mixed, the attributes new value if key has a current value
            that evaluates to False
        """
        if not self.fields.get(key, None):
            self.fields[key] = val

    def geturl(self):
        """return the dsn back into url form"""
        return urlparse.urlunparse((
            self.scheme,
            self.netloc,
            self.path,
            self.params,
            self.query,
            self.fragment,
        ))


def parse_environs(name, parse_class=ParseResult, **kwargs):
    """Similar to parse_environ() but will also check name_1, name_2, ..., name_N and
    return all the found dsn strings from the environment

    this will look for name, and name_N (where N is 1 through infinity) in the environment,
    if it finds them, it will assume they are dsn urls and will parse them. 

    The num checks (eg FOO_DSN_1, FOO_DSN_2) go in order, so you can't do FOO_DSN_1,
    FOO_DSN_3, because it will fail on _2 and move on, so make sure your num dsns
    are in order (eg, 1, 2, 3, ...)

    :Example:
        export FOO_DSN_1=some.Interface://host:port/dbname#i1
        export FOO_DSN_2=some.Interface://host2:port/dbname2#i2
        $ python
        >>> import dsnparse
        >>> print(dsnparse.parse_environs('FOO_DSN')) # list with 2 parsed dsn objects

    :param dsn_env_name: string, the name of the environment variables, _1, ... will be appended
    :param parse_class: ParseResult, the class that will be used to hold parsed values
    :returns: list[ParseResult], all the found dsn strings in the environment with
        the given name prefix
    """
    ret = []
    if name in os.environ:
        ret.append(parse_environ(name, parse_class, **kwargs))

    # now try importing _1 -> _N dsns
    increment_name = lambda name, num: '{name}_{num}'.format(name=name, num=num)
    dsn_num = 0 if increment_name(name, 0) in os.environ else 1
    dsn_env_num_name = increment_name(name, dsn_num)
    if dsn_env_num_name in os.environ:
        try:
            while True:
                ret.append(parse_environ(dsn_env_num_name, parse_class, **kwargs))
                dsn_num += 1
                dsn_env_num_name = increment_name(name, dsn_num)

        except KeyError:
            pass

    return ret


def parse_environ(name, parse_class=ParseResult, **kwargs):
    """
    same as parse() but you pass in an environment variable name that will be used
    to fetch the dsn

    :param name: str, the environment variable name that contains the dsn to parse
    :param parse_class: ParseResult, the class that will be used to hold parsed values
    :param **kwargs: dict, any values you want to have defaults for if they aren't in the dsn
    :returns: ParseResult instance
    """
    return parse(os.environ[name], parse_class, **kwargs)


def parse(dsn, parse_class=ParseResult, **kwargs):
    """
    parse a dsn to parts similar to parseurl

    :param dsn: string, the dsn to parse
    :param parse_class: ParseResult, the class that will be used to hold parsed values
    :param **kwargs: dict, any values you want to have defaults for if they aren't in the dsn
    :returns: ParseResult() tuple-like instance
    """
    r = parse_class(dsn, **kwargs)
    return r

