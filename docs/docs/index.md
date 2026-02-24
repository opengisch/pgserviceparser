# pgserviceparser

A Python package for parsing and editing the PostgreSQL [connection service file](https://www.postgresql.org/docs/current/libpq-pgservice-file.html) (`pg_service.conf`).

## Features

- **Read & write** service entries and their settings.
- **Create, rename, duplicate, and remove** services programmatically.
- **Copy settings** between services.
- **GUI application** for interactive management (install with `pip install pgserviceparser[gui]`).

## Quick start

```bash
pip install pgserviceparser
```

```python
import pgserviceparser

# List configured services
pgserviceparser.service_names()

# Read settings for a service
pgserviceparser.service_config("my-service")

# Write settings back
pgserviceparser.write_service("my-service", {"host": "localhost", "dbname": "mydb"})
```

Explore the [API reference](api.md) for the full list of functions or jump to the [GUI](gui.md) documentation.
