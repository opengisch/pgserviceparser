# pgserviceparser

A python package parsing the PostgreSQL connection service file.

```python
>>> import pgserviceparser
```

## Finding the PostgreSQL connection service file with `conf_path`

Returns the path found for the pg_service.conf on the system as string.

```python
>>> pgserviceparser.conf_path()
'/home/dave/.pg_service.conf'
```

## Listing all the services with `service_names`

Returns all service names in a list.
Optionally you can pass a config file path. Otherwise it gets it by `conf_path`.

```python
>>> pgserviceparser.service_names()
['srvce_wandplaene', 'ktn_solothurn', 'daves_bakery']

```

## Receiving the configuration for a service with `service_config`

Returns the config from the given service name as a dict.
Optionally you can pass a config file path. Otherwise it gets it by `conf_path`.

```python
>>> pgserviceparser.service_config('daves_bakery')
{'host': 'localhost', 'port': '5432', 'dbname': 'bakery', 'user': 'dave', 'password': 'fischersfritz'}
```

## Getting the full configuration with `full_config`

Returns full pgservice config as [configparser.ConfigParser()](https://docs.python.org/3/library/configparser.html).
Optionally you can pass a config file path. Otherwise it gets it by `conf_path`.

```python
>>> pgserviceparser.full_config()
<configparser.ConfigParser object at 0x7f4c6d66b580>
```

## Add a new service or remove one

Add a new service:

```python
import pgserviceparser
new_srv_settings = {"host": "localhost", "dbname": "best_database_ever", "port": 5432, "user": "ro_gis_user"}
new_srv = pgserviceparser.write_service(service_name="gis_prod_ro", settings=new_srv_settings, create_if_not_found=True)
assert isinstance(new_srv, dict)
```

The PG service file has now:

```ini
[gis_prod_ro]
host=localhost
dbname=best_database_ever
port=5432
user=ro_gis_user
```

To remove it:

```python
pgserviceparser.remove_service("gis_prod_ro")
```

----

## Contribute

### Test

```sh
pip install -e .[dev]
export PGSERVICEPARSER_SRC_DIR=$pwd
python -m unittest test.test_lib
```

### Git hooks

```sh
pip install pre-commit
pre-commit install
```

### Build documentation

```sh
pip install -e .[docs]
mkdocs build -f docs/mkdocs.yml
```
