# dsnparse

Parse [dsn connection url strings](http://en.wikipedia.org/wiki/Data_source_name). Responsible for parsing dsn strings in projects like [prom](https://github.com/jaymon/prom) and [morp](https://github.com/jaymon/morp).

This is a generic version of [dj-database-url](https://github.com/kennethreitz/dj-database-url).

So, now you can create dsns like this:

    scheme://user:pass@host:port/path?query=query_val#fragment

For example, let's look at a prom dsn:

    prom.interface.postgres.Interface://testuser:testpw@localhost/testdb

Now let's parse it:

```python
import dsnparse

dsn = "prom.interface.postgres.Interface://testuser:testpw@localhost:1234/testdb"
r = dsnparse.parse(dsn)

print(r.scheme) # prom.interface.postgres.Interface
print(r.username) # testuser
print(r.password) # testpw
print(r.host) # localhost
print(r.port) # 1234
print(r.hostloc) # localhost:1234
print(r.paths) # ['testdb']
```

Also, dsnparse can easily use environment variables:

```python
r = dsnparse.parse_environ('ENVIRONMENT_VARIABLE_NAME')
```

I tried to keep the interface very similar to [urlparse](https://docs.python.org/3/library/urllib.parse.html#urllib.parse.urlparse) so it will feel familiar to use.


## Customizing

By default, `dsnparse.parse(dsn)` returns a `ParseResult` instance, but that can be customized:

```python
import dsnparse

class MyResult(dsnparse.ParseResult):
    def configure(self):
        # expose an interface property
        self.interface = self.scheme

dsn = "Interface://testuser:testpw@localhost:1234/testdb"
r = dsnparse.parse(dsn, parse_class=MyResult)
print(isinstance(r, MyResult)) # True
print(r.interface) # Interface
```


## Install

Use pip:

    pip install dsnparse

or use pip with github:

    pip install -U "git+https://github.com/Jaymon/dsnparse#egg=dsnparse"

