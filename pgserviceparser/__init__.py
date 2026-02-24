# standard library
import configparser
import io
import platform
import stat
from os import getenv
from pathlib import Path
from typing import Optional

# package
from .exceptions import ServiceFileNotFound, ServiceNotFound


def _make_file_writable(path: Path):
    """Attempt to add write permissions to a file.

    Args:
        path: path to the file

    Raises:
        PermissionError: when the file permissions cannot be changed
    """
    current_permission = stat.S_IMODE(path.stat().st_mode)
    WRITE = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
    path.chmod(current_permission | WRITE)


def _when_read_only_try_to_add_write_permission(func):
    """Decorator for functions that attempt to modify the service file.

    If the file is read-only, a PermissionError exception will be raised.
    This decorator handles that error by attempting to set write permissions
    (which works if the user is the owner of the file or has proper rights to
    alter the file permissions), and rerunning the decorated function.

    If the user cannot modify permissions on the file, the PermissionError
    is re-raised.
    """

    def wrapper(*args, **kwargs):
        attempt = 0
        while attempt <= 1:
            try:
                return func(*args, **kwargs)
            except PermissionError:
                if attempt == 1:
                    raise

                try:
                    _make_file_writable(conf_path())
                except PermissionError:
                    pass
                finally:
                    attempt += 1

    return wrapper


def conf_path(create_if_missing: bool | None = False) -> Path:
    """Returns the path found for the pg_service.conf on the system as string.

    Args:
        create_if_missing: Whether to create the file (and eventually its parent folders) if the file does not exist.

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

    if create_if_missing and not pg_config_path.exists():
        # Make sure all parent directories exist
        if not pg_config_path.parent.exists():
            pg_config_path.parent.mkdir(parents=True, exist_ok=True)

        # Finally, make sure the file itself exists
        Path.touch(pg_config_path)

    return pg_config_path


def full_config(conf_file_path: Path | None = None) -> configparser.ConfigParser:
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

    config = configparser.ConfigParser(interpolation=None)
    config.read(conf_file_path)
    return config


@_when_read_only_try_to_add_write_permission
def remove_service(service_name: str, conf_file_path: Path | None = None) -> None:
    """Remove a complete service from the service file.

    Args:
        service_name: service name
        conf_file_path: path to the pg_service.conf. If None the `conf_path()` is used,
            defaults to None

    Raises:
        ServiceFileNotFound: when the service file is not found
        ServiceNotFound: when the service is not found
        PermissionError: when the service file is read-only
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


@_when_read_only_try_to_add_write_permission
def rename_service(old_name: str, new_name: str, conf_file_path: Path | None = None) -> None:
    """Rename a service in the service file.

    The service settings are preserved under the new name and the old
    section is removed.

    Args:
        old_name: current service name
        new_name: desired service name
        conf_file_path: path to the pg_service.conf. If None the `conf_path()` is used,
            defaults to None

    Raises:
        ServiceFileNotFound: when the service file is not found
        ServiceNotFound: when the old service is not found
        PermissionError: when the service file is read-only
    """
    config = full_config(conf_file_path)
    if old_name not in config:
        raise ServiceNotFound(
            service_name=old_name,
            existing_service_names=service_names(),
            pg_service_filepath=conf_file_path or conf_path(),
        )

    settings = dict(config[old_name])
    config.remove_section(old_name)
    config[new_name] = settings
    with open(conf_file_path or conf_path(), "w") as configfile:
        config.write(configfile, space_around_delimiters=False)


@_when_read_only_try_to_add_write_permission
def create_service(service_name: str, settings: dict, conf_file_path: Path | None = None) -> bool:
    """Create a new service in the service file.

    If the service already exists, nothing is changed and False is returned.

    Args:
        service_name: service name
        settings: settings dict defining the service config
        conf_file_path: path to the pg_service.conf. If None the `conf_path()` is used,
            defaults to None

    Returns:
        True if the service was created, False if it already existed

    Raises:
        ServiceFileNotFound: when the service file is not found
        PermissionError: when the service file is read-only
    """
    config = full_config(conf_file_path)
    if service_name in config:
        return False

    config[service_name] = settings.copy()
    with open(conf_file_path or conf_path(), "w") as configfile:
        config.write(configfile, space_around_delimiters=False)

    return True


@_when_read_only_try_to_add_write_permission
def copy_service_settings(
    source_service_name: str,
    target_service_name: str,
    conf_file_path: Path | None = None,
) -> bool:
    """Copy all settings from one service to another.

    If the target service does not exist, it is created.

    Args:
        source_service_name: name of the service to copy settings from
        target_service_name: name of the service to copy settings to
        conf_file_path: path to the pg_service.conf. If None the `conf_path()` is used,
            defaults to None

    Returns:
        True on success

    Raises:
        ServiceFileNotFound: when the service file is not found
        ServiceNotFound: when the source service is not found
        PermissionError: when the service file is read-only
    """
    config = full_config(conf_file_path)
    if source_service_name not in config:
        raise ServiceNotFound(
            service_name=source_service_name,
            existing_service_names=service_names(),
            pg_service_filepath=conf_file_path or conf_path(),
        )

    settings = dict(config[source_service_name])
    config[target_service_name] = settings
    with open(conf_file_path or conf_path(), "w") as configfile:
        config.write(configfile, space_around_delimiters=False)

    return True


def service_config(service_name: str, conf_file_path: Path | None = None) -> dict:
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


@_when_read_only_try_to_add_write_permission
def write_service_setting(
    service_name: str,
    setting_key: str,
    setting_value: str,
    conf_file_path: Path | None = None,
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
        PermissionError: when the service file is read-only
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


@_when_read_only_try_to_add_write_permission
def write_service(
    service_name: str, settings: dict, conf_file_path: Path | None = None, create_if_not_found: bool = False
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
        PermissionError: when the service file is read-only

    Returns:
        existing or newly created service as dictionary
    """

    config = full_config(conf_path(create_if_missing=create_if_not_found))

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


def write_service_to_text(service_name: str, settings: dict) -> str:
    """Returns the complete service settings as a string.

    Args:
        service_name: service name
        settings: settings dict defining the service config

    Returns:
        Service settings as a string
    """
    config = configparser.ConfigParser(interpolation=None)
    config[service_name] = settings.copy()

    config_stream = io.StringIO()
    config.write(config_stream, space_around_delimiters=False)
    res = config_stream.getvalue()
    config_stream.close()

    return res.strip()


def service_names(conf_file_path: Path | None = None, sorted_alphabetically: bool = False) -> list[str]:
    """Returns all service names in a list.

    Args:
        conf_file_path: path to the pg_service.conf. If None the `conf_path()` is used, defaults to None
        sorted_alphabetically: whether to sort the names alphabetically (case-insensitive),
            defaults to False

    Returns:
        list of every service registered

    Raises:
        ServiceFileNotFound: when the service file is not found
    """

    config = full_config(conf_file_path)
    names = config.sections()
    return sorted(names, key=str.lower) if sorted_alphabetically else names
