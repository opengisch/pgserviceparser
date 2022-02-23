import configparser
import os

def conf_path():
    # Path for pg_service.conf
    pg_config_path = None
    if os.environ.get("PGSERVICEFILE"):
        pg_config_path = os.environ.get("PGSERVICEFILE")
    elif os.environ.get("PGSYSCONFDIR"):
        pg_config_path = os.path.join(os.environ.get("PGSYSCONFDIR"), "pg_service.conf")
    else:
        pg_config_path = "~/.pg_service.conf"
    return os.path.expanduser(pg_config_path)
 
def full_config( conf_file_path = None ):
    # Returns full pgservice config as ConfigParser()
    if conf_file_path is None:
        conf_file_path = conf_path()

    config = configparser.ConfigParser()
    if os.path.exists(conf_file_path):
        config.read(conf_file_path)
    return config

def service_config(service_name, conf_file_path = None):
    """
    Returns a config object from a service name
    """
    config = full_config(conf_file_path)
    return config[service_name]

def service_names(conf_file_path = None):
    """
    Returns all service names as list
    """
    config = full_config(conf_file_path)
    return config.sections()
