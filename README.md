# dsnparse

Parse [dsn connection url strings](http://en.wikipedia.org/wiki/Data_source_name). I kept duplicating dsn parsing code for things like [prom](https://github.com/firstopinion/prom) and morp, and I realized I was going to need many more dsn urls in the future so I decided to create something a little more modular.

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

print r.scheme # prom.interface.postgres.Interface
print r.username # testuser
print r.password # testpw
print r.host # localhost
print r.hostloc # localhost:1234
print r.paths # ['testdb']
```

Also, dsnparse can easily use environment variables:

```python
r = dsnparse.parse_environ('ENVIRONMENT_VARIABLE_NAME')
```

I tried to keep the interface very similar to `urlparse` so it will feel familiar to use.

## Example

By default, `dsnparse.parse(dsn)` returns a `ParseResult` instance, but that can be customized:

```python
import dsnparse

class MyResult(dsnparse.ParseResult):
    @classmethod
    def parse(cls, dsn, **defaults):
        d = super(MyResult, cls).parse(dsn, **defaults)
        # d is a dict and you can customize its keys/values here
        d["interface"] = d.pop("scheme")
        return d

dsn = "Interface://testuser:testpw@localhost:1234/testdb"
r = dsnparse.parse(dsn, parse_class=MyResult)
print isinstance(r, MyResult) # True
print r.interface # Interface
```


## Install

Use pip:

    pip install dsnparse

or use pip with github:

    pip install git+https://github.com/Jaymon/dsnparse#egg=dsnparse

## License

MIT
