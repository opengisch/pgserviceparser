# pgserviceparser
A python package parsing the PostgreSQL connection service file.

```
>>> import pgserviceparser
```

## Finding the PostgreSQL connection service file with `conf_path`

Returns the path found for the pg_service.conf on the system as string.
```
>>> pgserviceparser.conf_path()
'/home/dave/.pg_service.conf'
```
## Listing all the services with `service_names`

Returns all service names in a list.
Optionally you can pass a config file path. Otherwise it gets it by `conf_path`.
```
>>> pgserviceparser.service_names()
['srvce_wandplaene', 'ktn_solothurn', 'daves_bakery']
```
## Receiving the configuration for a service with `service_config`

Returns the config from the given service name as a dict.
Optionally you can pass a config file path. Otherwise it gets it by `conf_path`.
```
>>> pgserviceparser.service_config('daves_bakery')
{'host': 'localhost', 'port': '5432', 'dbname': 'bakery', 'user': 'dave', 'password': 'fischersfritz'}
```

## Getting the full configuration with `full_config`

Returns full pgservice config as configparser.ConfigParser().
Optionally you can pass a config file path. Otherwise it gets it by `conf_path`.
```
>>> pgserviceparser.full_config()
<configparser.ConfigParser object at 0x7f4c6d66b580>
```
