# standard library
import configparser
import io
import platform
import re
import stat
from collections.abc import Iterable, Iterator
from enum import Enum
from os import getenv
from pathlib import Path
from typing import Optional

# package
from .exceptions import ServiceFileNotFound, ServiceNotFound

try:
    from .gui import PGServiceParserWidget  # noqa: F401
except ImportError:
    pass

# Header of a disabled (commented out) service, e.g. "#[my_service]"
_DISABLED_SERVICE_HEADER = re.compile(r"#\s*\[(?P<header>[^]]+)\]")
# Following lines of a disabled service: empty, comment or setting
_DISABLED_SERVICE_LINE = re.compile(r"#(\s*|[#;].*|\s*\w+\s*=.*)")


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


class ConfPathSource(Enum):
    """How the path returned by `conf_path` is determined."""

    PGSERVICEFILE = "PGSERVICEFILE"
    """Set by the PGSERVICEFILE environment variable."""
    PGSYSCONFDIR = "PGSYSCONFDIR"
    """pg_service.conf in the directory set by the PGSYSCONFDIR environment variable."""
    DEFAULT = "DEFAULT"
    """Default location of the platform."""


def conf_path_source() -> ConfPathSource:
    """Returns how the path returned by `conf_path` is determined.

    Returns:
        the source of the pg_service.conf path
    """
    if getenv("PGSERVICEFILE"):
        return ConfPathSource.PGSERVICEFILE
    if getenv("PGSYSCONFDIR"):
        return ConfPathSource.PGSYSCONFDIR
    return ConfPathSource.DEFAULT


def conf_path(create_if_missing: bool | None = False) -> Path:
    """Returns the path found for the pg_service.conf on the system as string.

    Use `conf_path_source` to know how this path is determined.

    Args:
        create_if_missing: Whether to create the file (and eventually its parent folders) if the file does not exist.

    Returns:
        path to the pg_service.conf file as string
    """
    pg_config_path = None
    source = conf_path_source()
    if source == ConfPathSource.PGSERVICEFILE:
        pg_config_path = Path(getenv("PGSERVICEFILE"))
    elif source == ConfPathSource.PGSYSCONFDIR:
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


def _skip_duplicates(lines: Iterable[str]) -> Iterator[str]:
    """Skips the duplicated services and settings of a service file.

    Like libpq, only the first occurrence of a service and the first occurrence
    of a setting within a service are kept.

    Args:
        lines: lines of the service file

    Yields:
        lines of the service file without the duplicates
    """
    services = set()
    settings = set()
    skip_service = False
    for line in lines:
        stripped = line.strip()
        if header := configparser.ConfigParser.SECTCRE.match(stripped):
            service = header.group("header")
            skip_service = service in services
            services.add(service)
            settings = set()
        elif skip_service:
            continue
        elif not stripped.startswith(("#", ";")) and (option := configparser.ConfigParser.OPTCRE.match(stripped)):
            setting = option.group("option").lower()
            if setting in settings:
                continue
            settings.add(setting)

        if not skip_service:
            yield line


def full_config(conf_file_path: Path | None = None) -> configparser.ConfigParser:
    """Returns full pgservice config as configparser.ConfigParser().

    Like libpq, if a service or a setting within a service is duplicated, only the
    first occurrence is used. The other occurrences are removed when writing the file.

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
    with open(conf_file_path) as f:
        config.read_file(_skip_duplicates(f), source=str(conf_file_path))
    return config


def _read_lines(conf_file_path: Path) -> list[str]:
    """Returns the lines of the service file.

    Raises:
        ServiceFileNotFound: when the service file is not found
    """
    if not conf_file_path.exists():
        raise ServiceFileNotFound(pg_service_filepath=conf_file_path)

    return conf_file_path.read_text().splitlines(keepends=True)


def _disabled_service_ranges(lines: list[str]) -> list[tuple[str, int, int]]:
    """Returns the name and the line range of the disabled services.

    A disabled service is a commented out header (e.g. ``#[my_service]``),
    followed by commented out settings, comments and empty lines.
    """
    ranges = []
    for start, line in enumerate(lines):
        if header := _DISABLED_SERVICE_HEADER.fullmatch(line.strip()):
            end = start + 1
            while end < len(lines) and _DISABLED_SERVICE_LINE.fullmatch(lines[end].strip()):
                end += 1
            ranges.append((header.group("header"), start, end))
    return ranges


def _disabled_service_range(lines: list[str], service_name: str, conf_file_path: Path) -> tuple[int, int]:
    """Returns the line range of the first disabled service with the given name.

    Raises:
        ServiceNotFound: when no disabled service has this name
    """
    ranges = _disabled_service_ranges(lines)
    for name, start, end in ranges:
        if name == service_name:
            return start, end

    raise ServiceNotFound(
        service_name=service_name,
        existing_service_names=[name for name, _, _ in ranges],
        pg_service_filepath=conf_file_path,
    )


def _uncomment(line: str) -> str:
    return re.sub(r"#[ \t]*", "", line, count=1)


def _write_config(config: configparser.ConfigParser, conf_file_path: Path) -> None:
    """Writes the config to the service file, keeping the disabled services at the end."""
    lines = Path(conf_file_path).read_text().splitlines(keepends=True)
    disabled = ["".join(lines[start:end]).rstrip("\n") + "\n\n" for _, start, end in _disabled_service_ranges(lines)]
    with open(conf_file_path, "w") as configfile:
        config.write(configfile, space_around_delimiters=False)
        configfile.writelines(disabled)


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
    _write_config(config, conf_file_path or conf_path())


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
    _write_config(config, conf_file_path or conf_path())


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
    _write_config(config, conf_file_path or conf_path())

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
    _write_config(config, conf_file_path or conf_path())

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
    _write_config(config, conf_file_path or conf_path())


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
    _write_config(config, conf_file_path or conf_path())

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


@_when_read_only_try_to_add_write_permission
def disable_service(service_name: str, conf_file_path: Path | None = None) -> None:
    """Disables a service by commenting it out in the service file.

    The rest of the file is left untouched. The disabled service is kept when
    the service file is written and can be restored with `enable_service`.

    Args:
        service_name: service name
        conf_file_path: path to the pg_service.conf. If None the `conf_path()` is used,
            defaults to None

    Raises:
        ServiceFileNotFound: when the service file is not found
        ServiceNotFound: when the service is not found
        PermissionError: when the service file is read-only
    """
    conf_file_path = Path(conf_file_path or conf_path())
    names = service_names(conf_file_path)
    if service_name not in names:
        raise ServiceNotFound(
            service_name=service_name,
            existing_service_names=names,
            pg_service_filepath=conf_file_path,
        )

    lines = _read_lines(conf_file_path)
    headers = [
        (i, header.group("header"))
        for i, line in enumerate(lines)
        if (header := configparser.ConfigParser.SECTCRE.match(line.strip()))
    ]
    ends = [i for i, _ in headers[1:]] + [len(lines)]
    for (start, name), end in zip(headers, ends):
        if name != service_name:
            continue
        # Leave the trailing empty lines and comments to the next service
        while not lines[end - 1].strip() or lines[end - 1].lstrip().startswith(("#", ";")):
            end -= 1
        for i in range(start, end):
            lines[i] = f"#{lines[i]}"

    conf_file_path.write_text("".join(lines))


@_when_read_only_try_to_add_write_permission
def enable_service(service_name: str, conf_file_path: Path | None = None) -> bool:
    """Enables a disabled service by uncommenting it in the service file.

    If several disabled services have the same name, the first one is enabled.
    If a service with the same name already exists, nothing is changed and False is returned.

    Args:
        service_name: service name
        conf_file_path: path to the pg_service.conf. If None the `conf_path()` is used,
            defaults to None

    Returns:
        True if the service was enabled, False if a service with the same name already exists

    Raises:
        ServiceFileNotFound: when the service file is not found
        ServiceNotFound: when no disabled service has this name
        PermissionError: when the service file is read-only
    """
    conf_file_path = Path(conf_file_path or conf_path())
    lines = _read_lines(conf_file_path)
    start, end = _disabled_service_range(lines, service_name, conf_file_path)
    if service_name in service_names(conf_file_path):
        return False

    lines[start:end] = [_uncomment(line) for line in lines[start:end]]
    conf_file_path.write_text("".join(lines))
    return True


def disabled_service_names(conf_file_path: Path | None = None) -> list[str]:
    """Returns the names of the disabled services in a list.

    Args:
        conf_file_path: path to the pg_service.conf. If None the `conf_path()` is used, defaults to None

    Returns:
        list of every disabled service

    Raises:
        ServiceFileNotFound: when the service file is not found
    """
    lines = _read_lines(Path(conf_file_path or conf_path()))
    return list(dict.fromkeys(name for name, _, _ in _disabled_service_ranges(lines)))


def disabled_service_config(service_name: str, conf_file_path: Path | None = None) -> dict:
    """Returns the config of a disabled service as a dict.

    If several disabled services have the same name, the first one is used.

    Args:
        service_name: service name
        conf_file_path: path to the pg_service.conf. If None the `conf_path()` is used, defaults to None

    Returns:
        service settings as dictionary

    Raises:
        ServiceFileNotFound: when the service file is not found
        ServiceNotFound: when no disabled service has this name
    """
    conf_file_path = Path(conf_file_path or conf_path())
    lines = _read_lines(conf_file_path)
    start, end = _disabled_service_range(lines, service_name, conf_file_path)

    config = configparser.ConfigParser(interpolation=None)
    config.read_string("".join(_uncomment(line) for line in lines[start:end]))
    return dict(config[service_name])
