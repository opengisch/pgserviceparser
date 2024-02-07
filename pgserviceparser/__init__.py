import configparser
import os


def conf_path() -> str:
    """Returns the path found for the pg_service.conf on the system as string.

    :return str: path to the pg_service.conf file as string
    """
    pg_config_path = None
    if os.environ.get("PGSERVICEFILE"):
        pg_config_path = os.environ.get("PGSERVICEFILE")
    elif os.environ.get("PGSYSCONFDIR"):
        pg_config_path = os.path.join(os.environ.get("PGSYSCONFDIR"), "pg_service.conf")
    else:
        pg_config_path = "~/.pg_service.conf"
    return os.path.expanduser(pg_config_path)

def full_config(conf_file_path: str = None) -> configparser.ConfigParser:
    """Returns full pgservice config as configparser.ConfigParser().

    :param str conf_file_path: path to configuration file to load. If None the `conf_path` is used, defaults to None

    :return configparser.ConfigParser: pg services loaded as ConfigParser
    """
    if conf_file_path is None:
        conf_file_path = conf_path()

    config = configparser.ConfigParser()
    if os.path.exists(conf_file_path):
        config.read(conf_file_path)
    return config


def service_config(service_name: str, conf_file_path: str = None) -> dict:
    """Returns the config from the given service name as a dict.

    :param str service_name: service name
    :param str conf_file_path: path to the pg_service.conf. If None the `conf_path` is used, defaults to None

    :return dict: service settings as dictionary
    """
    config = full_config(conf_file_path)
    if service_name in config:
        return dict(config[service_name])
    return {}

def write_service_setting(
    service_name: str, setting_key: str, setting_value: str, conf_file_path: str = None
) -> bool:
    """Returns true if it could write the setting to the file.

    :param str service_name: service's name
    :param str setting_key: key
    :param str setting_value: value
    :param str conf_file_path: path to the pg_service.conf. If None the `conf_path()` is used, defaults to None

    :return bool: True if the setting has been successfully written
    """
    config = full_config(conf_file_path)
    if service_name in config:
        config[service_name][setting_key] = setting_value
        with open(conf_file_path or conf_path(), "w") as configfile:
            config.write(configfile)
            return True
    return False


def service_names(conf_file_path: str = None) -> list:
    """Returns all service names in a list.

    :param str conf_file_path: path to the pg_service.conf. If None the `conf_path()` is used, defaults to None
    :return list: list of every service registered
    """
    config = full_config(conf_file_path)
    return config.sections()
