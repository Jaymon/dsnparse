# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse
import re
import os


__version__ = '0.1.5'


def parse_environ(name, **defaults):
    """
    same as parse() but you pass in an environment variable name that will be used
    to fetch the dsn

    :param name: string, the environment variable name that contains the dsn to parse
    :param **defaults: dict, any values you want to have defaults for if they aren't in the dsn
    :returns: ParseResult() tuple
    """
    return parse(os.environ[name], **defaults)


def parse_environs(name, **defaults):
    """
    same as parse_environ() but will also check name_1, name_2, ..., name_N and
    return all the found dsn strings from the environment

    this will look for name, and name_N (where N is 1 through infinity) in the environment,
    if it finds them, it will assume they are dsn urls and will parse them. 

    The num checks (eg PROM_DSN_1, PROM_DSN_2) go in order, so you can't do PROM_DSN_1, PROM_DSN_3,
    because it will fail on _2 and move on, so make sure your num dsns are in order (eg, 1, 2, 3, ...)

    example --
        export DSN_1=some.Interface://host:port/dbname#i1
        export DSN_2=some.Interface://host2:port/dbname2#i2
        $ python
        >>> import dsnparse
        >>> print dsnparse.parse_environs('DSN') # prints list with 2 parsed dsn objects

    :param dsn_env_name: string, the name of the environment variables, _1, ... will be appended
    :returns: list all the found dsn strings in the environment with the given name prefix
    """
    ret = []
    if name in os.environ:
        ret.append(parse_environ(os.environ[dsn_env_name], **defaults))

    # now try importing _1 -> _N dsns
    increment_name = lambda name, num: '{}_{}'.format(name, num)
    dsn_num = 0 if increment_name(dsn_env_name, 0) in os.environ else 1
    dsn_env_num_name = increment_name(dsn_env_name, dsn_num)
    if dsn_env_num_name in os.environ:
        try:
            while True:
                ret.append(parse_environ(os.environ[dsn_env_num_name], **defaults))
                dsn_num += 1
                dsn_env_num_name = increment_name(dsn_env_name, dsn_num)

        except KeyError:
            pass

    return ret


def parse(dsn, **defaults):
    """
    parse a dsn to parts similar to parseurl

    this is a nuts function that can serve as a good basis to parsing a custom dsn

    :param dsn: string, the dsn to parse
    :param **defaults: dict, any values you want to have defaults for if they aren't in the dsn
    :returns: ParseResult() tuple
    """
    if not re.match("^\S+://\S+", dsn):
        raise ValueError("{} is invalid, only full dsn urls (scheme://host...) allowed".format(dsn))

    first_colon = dsn.find(':')
    scheme = dsn[0:first_colon]
    dsn_url = dsn[first_colon+1:]
    url = urlparse.urlparse(dsn_url)

    hostname = url.hostname
    path = url.path

    if url.netloc == ":memory:":
        # the special :memory: signifier is used in SQLite to define a fully in
        # memory database, I think it makes sense to support it since dsnparse is all
        # about making it easy to parse *any* dsn
        path = url.netloc
        hostname = None
        port = None

    else:
        # compensate for relative path
        if url.hostname == "." or url.hostname == "..":
            path = "".join([hostname, path])
            hostname = None

        port = url.port

    # parse the query into options
    options = {}
    if url.query:
        for k, kv in urlparse.parse_qs(url.query, True, True).items():
            if len(kv) > 1:
                options[k] = kv
            else:
                options[k] = kv[0]

    r = ParseResult(
        scheme=scheme,
        hostname=hostname,
        path=path,
        params=url.params,
        query=options,
        fragment=url.fragment,
        username=url.username,
        password=url.password,
        port=port,
        query_str=url.query,
    )
    for k, v in defaults.items():
        r.setdefault(k, v)

    return r


class ParseResult(object):
    """
    hold the results of a parsed dsn

    this is very similar to urlparse.ParseResult tuple

    http://docs.python.org/2/library/urlparse.html#results-of-urlparse-and-urlsplit

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
        query -- a dict of the query string
        query_str -- the raw query string
        port
        fragment
        anchor -- same as fragment, just an alternative name
    """
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __iter__(self):
        mapping = ['scheme', 'netloc', 'path', 'params', 'query', 'fragment']
        for k in mapping:
            yield getattr(self, k, '')

    def __getitem__(self, index):
        index = int(index)
        mapping = {
            0: 'scheme',
            1: 'netloc',
            2: 'path',
            3: 'params',
            4: 'query',
            5: 'fragment',
        }

        return getattr(self, mapping[index], '')

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
            s += ":{}".format(self.password)
            prefix = '@'

        s += "{}{}".format(prefix, self.hostloc)
        return s

    @property
    def paths(self):
        """the path attribute split by /"""
        return list(filter(None, self.path.split('/')))

    @property
    def host(self):
        """the hostname, but I like host better"""
        return self.hostname

    @property
    def hostloc(self):
        """return host:port"""
        hostloc = self.hostname
        if self.port:
            hostloc = '{}:{}'.format(hostloc, self.port)

        return hostloc

    @property
    def anchor(self):
        """alternative name for the fragment"""
        return self.fragment

    def setdefault(self, key, val):
        """
        set a default value for key

        this is different than dict's setdefault because it will set default either
        if the key doesn't exist, or if the value at the key evaluates to False, so
        an empty string or a None will value will be updated

        key -- string -- the attribute to update
        val -- mixed -- the attributes new value if key has a current value that evaluates to False
        """
        if not getattr(self, key, None):
            setattr(self, key, val)

    def geturl(self):
        """return the dsn back into url form"""
        return urlparse.urlunparse((
            self.scheme,
            self.netloc,
            self.path,
            self.params,
            self.query_str,
            self.fragment,
        ))
