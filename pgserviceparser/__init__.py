# standard library
import configparser
import platform
from os import getenv
from pathlib import Path
from typing import Optional

# package
from .exceptions import ServiceFileNotFound, ServiceNotFound


def conf_path() -> Path:
    """Returns the path found for the pg_service.conf on the system as string.

    Returns:
        path to the pg_service.conf file as string
    """
    pg_config_path = None
    if getenv("PGSERVICEFILE"):
        pg_config_path = Path(getenv("PGSERVICEFILE"))
    elif getenv("PGSYSCONFDIR"):
        pg_config_path = Path(getenv("PGSYSCONFDIR")) / "pg_service.conf"
    else:
        if platform.system() == "Windows":
            pg_config_path = Path(getenv("APPDATA")) / "postgresql/.pg_service.conf"
        else:  # Linux or Darwin (Mac)
            pg_config_path = Path("~/.pg_service.conf").expanduser()

    return pg_config_path


def full_config(conf_file_path: Optional[Path] = None) -> configparser.ConfigParser:
    """Returns full pgservice config as configparser.ConfigParser().

    Args:
        conf_file_path: path to configuration file to load. If None the `conf_path` is used, defaults to None

    Returns:
        pg services loaded as ConfigParser

    Raises:
        ServiceFileNotFound: when the service file is not found
    """
    if conf_file_path is None:
        conf_file_path = conf_path()
    else:
        conf_file_path = Path(conf_file_path)

    if not conf_file_path.exists():
        raise ServiceFileNotFound(pg_service_filepath=conf_file_path)

    config = configparser.ConfigParser()
    config.read(conf_file_path)
    return config


def remove_service(service_name: str, conf_file_path: Optional[Path] = None) -> None:
    """Remove a complete service from the service file.

    Args:
        service_name: service name
        conf_file_path: path to the pg_service.conf. If None the `conf_path()` is used,
            defaults to None

    Raises:
        ServiceFileNotFound: when the service file is not found
        ServiceNotFound: when the service is not found
    """
    config = full_config(conf_file_path)
    if service_name not in config:
        raise ServiceNotFound(
            service_name=service_name,
            existing_service_names=service_names(),
            pg_service_filepath=conf_file_path or conf_path(),
        )

    config.remove_section(service_name)
    with open(conf_file_path or conf_path(), "w") as configfile:
        config.write(configfile, space_around_delimiters=False)


def service_config(service_name: str, conf_file_path: Optional[Path] = None) -> dict:
    """Returns the config from the given service name as a dict.

    Args:
        service_name: service name
        conf_file_path: path to the pg_service.conf. If None the `conf_path` is used, defaults to None

    Returns:
        service settings as dictionary

    Raises:
        ServiceNotFound: when the service is not found
    """
    config = full_config(conf_file_path)

    if service_name not in config:
        raise ServiceNotFound(
            service_name=service_name,
            existing_service_names=service_names(),
            pg_service_filepath=conf_file_path or conf_path(),
        )

    return dict(config[service_name])


def write_service_setting(
    service_name: str,
    setting_key: str,
    setting_value: str,
    conf_file_path: Optional[Path] = None,
):
    """Writes a service setting to the service file.

    Args:
        service_name: service name
        setting_key: key
        setting_value: value
        conf_file_path: path to the pg_service.conf. If None the `conf_path()` is used, defaults to None

    Raises:
        ServiceFileNotFound: when the service file is not found
        ServiceNotFound: when the service is not found
    """

    config = full_config(conf_file_path)
    if service_name not in config:
        raise ServiceNotFound(
            service_name=service_name,
            existing_service_names=service_names(),
            pg_service_filepath=conf_file_path or conf_path(),
        )

    config[service_name][setting_key] = setting_value
    with open(conf_file_path or conf_path(), "w") as configfile:
        config.write(configfile, space_around_delimiters=False)


def write_service(
    service_name: str, settings: dict, conf_file_path: Optional[Path] = None, create_if_not_found: bool = False
) -> dict:
    """Writes a complete service to the service file.

    Args:
        service_name: service name
        settings: settings dict defining the service config
        conf_file_path: path to the pg_service.conf. If None the `conf_path()` is used,
            defaults to None
        create_if_not_found: option to create a new service if it does not exist yet.
            Defaults to False.

    Raises:
        ServiceFileNotFound: when the service file is not found
        ServiceNotFound: when the service is not found

    Returns:
        existing or newly created service as dictionary
    """
    config = full_config(conf_file_path)
    if service_name not in config and not create_if_not_found:
        raise ServiceNotFound(
            service_name=service_name,
            existing_service_names=service_names(),
            pg_service_filepath=conf_file_path or conf_path(),
        )

    config[service_name] = settings.copy()
    with open(conf_file_path or conf_path(), "w") as configfile:
        config.write(configfile, space_around_delimiters=False)

    return dict(config[service_name])


def service_names(conf_file_path: Optional[Path] = None) -> list[str]:
    """Returns all service names in a list.

    Args:
        conf_file_path: path to the pg_service.conf. If None the `conf_path()` is used, defaults to None

    Returns:
        list of every service registered

    Raises:
        ServiceFileNotFound: when the service file is not found
    """

    config = full_config(conf_file_path)
    return config.sections()
