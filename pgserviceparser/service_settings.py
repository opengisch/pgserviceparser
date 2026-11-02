"""PostgreSQL connection service settings definitions.

See https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-PARAMKEYWORDS
"""

from enum import Enum


class SslModeEnum(Enum):
    DISABLE = "disable"
    ALLOW = "allow"
    PREFER = "prefer"
    REQUIRE = "require"
    VERIFY_CA = "verify-ca"
    VERIFY_FULL = "verify-full"


class WidgetType(Enum):
    """Widget type hints for GUI editors."""

    PLAIN = 0
    COMBOBOX = 1
    FILE = 2
    PASSWORD = 3


# Settings available for manual addition.
SERVICE_SETTINGS: dict[str, dict] = {
    "host": {
        "default": "localhost",
        "description": "Name of host to connect to.",
    },
    "port": {
        "default": "5432",
        "description": "Port number to connect to at the server host.",
    },
    "dbname": {
        "default": "test",
        "description": "The database name.",
    },
    "user": {
        "default": "",
        "description": "PostgreSQL user name to connect as.",
    },
    "password": {
        "default": "",
        "description": "Password to be used if the server demands password authentication.",
        "widget_type": WidgetType.PASSWORD,
    },
    "passfile": {
        "default": "",
        "description": "Specifies the name of the file used to store passwords.",
        "widget_type": WidgetType.FILE,
        "config": {
            "filter": "Password file (*.pgpass *.conf)",
            "title": "Select a .pgpass or .conf file",
        },
    },
    "sslmode": {
        "default": SslModeEnum.PREFER.value,
        "description": (
            "This option determines whether or with what priority a secure SSL "
            "TCP/IP connection will be negotiated with the server."
        ),
        "widget_type": WidgetType.COMBOBOX,
        "config": {"values": [e.value for e in SslModeEnum]},
    },
    "sslrootcert": {
        "default": "",
        "description": (
            "Name of a file containing SSL certificate authority (CA) certificate(s).\n"
            "If the file exists, the server's certificate will be verified to be signed "
            "by one of these authorities."
        ),
        "widget_type": WidgetType.FILE,
        "config": {
            "filter": "SSL crt files (*.crt)",
            "title": "Select the file pointing to SSL CA certificate(s)",
        },
    },
    "sslcert": {
        "default": "",
        "description": (
            "Specifies the file name of the client SSL certificate, replacing "
            "the default ~/.postgresql/postgresql.crt."
        ),
        "widget_type": WidgetType.FILE,
        "config": {
            "filter": "SSL crt files (*.crt)",
            "title": "Select the client SSL certificate file",
        },
    },
    "sslkey": {
        "default": "",
        "description": "Specifies the location for the secret key used for the client certificate.",
        "widget_type": WidgetType.FILE,
        "config": {
            "filter": "SSL secret key files (*.key)",
            "title": "Select the secret key file",
        },
    },
}

# Settings to initialize new service files.
SETTINGS_TEMPLATE: dict[str, str] = {
    "host": "localhost",
    "port": "5432",
    "dbname": "test",
}
