import urlparse
import re
import os

__version__ = '0.1'

def parse_environ(name):
    """
    same as parse() but you pass in an environment variable name that will be used
    to fetch the dsn

    name -- string -- the environment variable name that contains the dsn to parse
    return -- ParseResult() tuple
    """
    return parse(os.environ[name])

def parse(dsn):
    """
    parse a dsn to parts similar to parseurl

    this is a nuts function that can serve as a good basis to parsing a custom dsn

    dsn -- string -- the dsn to parse
    return -- ParseResult() tuple
    """
    assert re.match("^\S+://\S+", dsn), "only full dsns with form: scheme://host... are supported"

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
        scheme,
        url.netloc,
        url.path,
        url.params,
        options,
        url.fragment,
        username=url.username,
        password=url.password,
        hostname=url.hostname,
        port=url.port,
        query_str=url.query,
    )
    return r

class ParseResult(urlparse.ParseResult):
    """
    hold the results of a parsed dsn

    this is very similar to urlparse.ParseResult tuple

    http://docs.python.org/2/library/urlparse.html#results-of-urlparse-and-urlsplit

    it exposes the following attributes --
        scheme
        schemes -- if your scheme has +'s in it, then this will contain a list of schemes split by +
        path
        paths -- the path segment split by /
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
    """
    @classmethod
    def __new__(cls, *args, **kwargs):
        # http://stackoverflow.com/questions/10788976/how-do-i-properly-inherit-from-a-superclass-that-has-a-new-method
        return urlparse.ParseResult.__new__(*args)

    def __init__(self, *args, **kwargs):
        super(ParseResult, self).__init__(*args)
        for k, v in kwargs.iteritems():
            self.__dict__[k] = v

    @property
    def schemes(self):
        """the scheme, split by plus signs"""
        return self.scheme.split('+')

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
        if self.port is not None:
            hostloc = '{}:{}'.format(hostloc, self.port)

        return hostloc

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

