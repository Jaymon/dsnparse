import urlparse
import re
import os

__version__ = '0.1.3'

def parse_environ(name, **default_vals):
    """
    same as parse() but you pass in an environment variable name that will be used
    to fetch the dsn

    name -- string -- the environment variable name that contains the dsn to parse
    **default_vals -- dict -- any values you want to have defaults for if they aren't in the dsn
    return -- ParseResult() tuple
    """
    return parse(os.environ[name], **default_vals)

def parse(dsn, **default_vals):
    """
    parse a dsn to parts similar to parseurl

    this is a nuts function that can serve as a good basis to parsing a custom dsn

    dsn -- string -- the dsn to parse
    **default_vals -- dict -- any values you want to have defaults for if they aren't in the dsn
    return -- ParseResult() tuple
    """
    assert re.match("^\S+://\S+", dsn), "{} is invalid, only full dsn urls (scheme://host...) allowed".format(dsn)

    first_colon = dsn.find(':')
    scheme = dsn[0:first_colon]
    dsn_url = dsn[first_colon+1:]
    url = urlparse.urlparse(dsn_url)

    # parse the query into options
    options = {}
    if url.query:
        for k, kv in urlparse.parse_qs(url.query, True, True).iteritems():
            if len(kv) > 1:
                options[k] = kv
            else:
                options[k] = kv[0]

    r = ParseResult(
        scheme=scheme,
        hostname=url.hostname,
        path=url.path,
        params=url.params,
        query=options,
        fragment=url.fragment,
        username=url.username,
        password=url.password,
        port=url.port,
        query_str=url.query,
    )
    for k, v in default_vals.iteritems():
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
        for k, v in kwargs.iteritems():
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
        return filter(None, self.path.split('/'))

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

