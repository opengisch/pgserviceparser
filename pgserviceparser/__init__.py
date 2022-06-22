import configparser
import os

def conf_path() -> str:
    """
    Returns the path found for the pg_service.conf on the system as string.
    """
    pg_config_path = None
    if os.environ.get("PGSERVICEFILE"):
        pg_config_path = os.environ.get("PGSERVICEFILE")
    elif os.environ.get("PGSYSCONFDIR"):
        pg_config_path = os.path.join(os.environ.get("PGSYSCONFDIR"), "pg_service.conf")
    else:
        pg_config_path = "~/.pg_service.conf"
    return os.path.expanduser(pg_config_path)
 
def full_config( conf_file_path: str = None ) -> configparser.ConfigParser:
    """
    Returns full pgservice config as configparser.ConfigParser().
    """
    if conf_file_path is None:
        conf_file_path = conf_path()

    config = configparser.ConfigParser()
    if os.path.exists(conf_file_path):
        config.read(conf_file_path)
    return config

def service_config(service_name: str, conf_file_path: str = None) -> dict:
    """
    Returns the config from the given service name as a dict.
    """
    config = full_config(conf_file_path)
    if service_name in config:
        return dict(config[service_name])
    return {}

def service_names(conf_file_path: str = None) -> list:
    """
    Returns all service names in a list.
    """
    config = full_config(conf_file_path)
    return config.sections()
