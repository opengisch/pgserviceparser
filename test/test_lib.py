#! /usr/bin/env python
import os
import shutil
import unittest
from pathlib import Path

from pgserviceparser import (
    ServiceNotFound,
    conf_path,
    service_config,
    service_names,
    write_service,
    write_service_setting,
)

PGSERVICEPARSER_SRC_PATH = Path(os.environ["PGSERVICEPARSER_SRC_DIR"])


class TestLib(unittest.TestCase):
    def setUp(self):
        service_file_path_base = PGSERVICEPARSER_SRC_PATH / "test" / "data" / "service_base.txt"
        service_file_path = PGSERVICEPARSER_SRC_PATH / "test" / "data" / "pgservice.conf"
        os.environ["PGSERVICEFILE"] = str(service_file_path)

        shutil.copy(service_file_path_base, service_file_path)

    def test_conf_path(self):
        self.assertEqual(Path(os.environ["PGSERVICEFILE"]), conf_path())

    def test_service_names(self):
        self.assertEqual(service_names(), ["service_1", "service_2", "service_3"])

    def test_service_config(self):
        self.assertRaises(ServiceNotFound, service_config, "non_existing_service")

        conf = service_config("service_1")
        self.assertEqual(
            conf, {"host": "host_1", "dbname": "db_1", "port": "1111", "user": "user_1", "password": "pwd_1"}
        )

    def test_write_service_setting(self):
        self.assertRaises(ServiceNotFound, write_service_setting, "non_existing_service", "key", "value")

        # Create setting
        write_service_setting("service_1", "new_key", "new_value")
        conf = service_config("service_1")
        self.assertIn("new_key", conf)
        self.assertEqual(conf["new_key"], "new_value")

        # Overwrite setting
        write_service_setting("service_1", "port", "1")
        conf = service_config("service_1")
        self.assertEqual(conf["port"], "1")

    def test_write_service(self):
        self.assertRaises(ServiceNotFound, write_service, "non_existing_service", {"key": "value"})

        # Overwrite the whole service_3 config using service_2 params
        config_3 = service_config("service_3")
        self.assertEqual(
            config_3, {"host": "host_3", "dbname": "db_3", "port": "3333", "user": "user_3", "password": "pwd_3"}
        )
        config_2 = service_config("service_2")
        write_service("service_3", config_2)
        self.assertEqual(service_config("service_3"), config_2)

    def tearDown(self):
        # Get back to initial status
        config = {"host": "host_1", "dbname": "db_1", "port": "1111", "user": "user_1", "password": "pwd_1"}
        write_service("service_1", config)

        config = {"host": "host_3", "dbname": "db_3", "port": "3333", "user": "user_3", "password": "pwd_3"}
        write_service("service_3", config)
