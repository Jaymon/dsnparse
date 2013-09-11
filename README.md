# dsnparse

Parse dsn connection url strings. I kept duplicating dsn parsing code for [prom](https://github.com/firstopinion/prom), and also for morp, and I realized I was going to need many more dsn urls in the future and I realized I was going to need something a little more modular.

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

## Install

Use pip:

    pip install dsnparse

or use github:

    pip install git+https://github.com/Jaymon/dsnparse#egg=dsnparse

## License

MIT
