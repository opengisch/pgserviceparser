import configparser
from os import getenv, path
from typing import Optional


def conf_path() -> str:
    """Returns the path found for the pg_service.conf on the system as string.

    Returns:
        path to the pg_service.conf file as string
    """
    pg_config_path = None
    if getenv("PGSERVICEFILE"):
        pg_config_path = getenv("PGSERVICEFILE")
    elif getenv("PGSYSCONFDIR"):
        pg_config_path = path.join(getenv("PGSYSCONFDIR"), "pg_service.conf")
    else:
        pg_config_path = "~/.pg_service.conf"
    return path.expanduser(pg_config_path)


def full_config(conf_file_path: Optional[str] = None) -> configparser.ConfigParser:
    """Returns full pgservice config as configparser.ConfigParser().

    Args:
        conf_file_path: path to configuration file to load. If None the `conf_path` is used, defaults to None

    Returns:
        pg services loaded as ConfigParser
    """
    if conf_file_path is None:
        conf_file_path = conf_path()

    config = configparser.ConfigParser()
    if path.exists(conf_file_path):
        config.read(conf_file_path)
    return config


def service_config(service_name: str, conf_file_path: Optional[str] = None) -> dict:
    """Returns the config from the given service name as a dict.

    Args:
        service_name: service name
        conf_file_path: path to the pg_service.conf. If None the `conf_path` is used, defaults to None

    Returns:
        service settings as dictionary
    """
    config = full_config(conf_file_path)
    if service_name in config:
        return dict(config[service_name])
    return {}


def write_service_setting(
    service_name: str,
    setting_key: str,
    setting_value: str,
    conf_file_path: Optional[str] = None,
) -> bool:
    """Returns true if it could write the setting to the file.

    Args:
        service_name: service's name
        setting_key: key
        setting_value: value
        conf_file_path: path to the pg_service.conf. If None the `conf_path()` is used, defaults to None

    Returns:
        True if the setting has been successfully written
    """

    config = full_config(conf_file_path)
    if service_name in config:
        config[service_name][setting_key] = setting_value
        with open(conf_file_path or conf_path(), "w") as configfile:
            config.write(configfile)
            return True
    return False


def write_service(
    service_name: str,
    settings: dict,
    conf_file_path: Optional[str] = None,
) -> bool:
    """Returns true if it could write the settings to the file.

    Args:
        service_name: service's name
        settings: settings dict defining the service config
        conf_file_path: path to the pg_service.conf. If None the `conf_path()` is used, defaults to None

    Returns:
        True if the setting has been successfully written
    """
    config = full_config(conf_file_path)
    if service_name in config:
        config[service_name] = settings.copy()
        with open(conf_file_path or conf_path(), "w") as configfile:
            config.write(configfile)
            return True
    return False


def service_names(conf_file_path: Optional[str] = None) -> list[str]:
    """Returns all service names in a list.

    Args:
        conf_file_path: path to the pg_service.conf. If None the `conf_path()` is used, defaults to None

    Returns:
        list of every service registered
    """
    config = full_config(conf_file_path)
    return config.sections()
