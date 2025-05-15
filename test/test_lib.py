#!/usr/bin/env python3

"""Library unit tests.

Usage from the repo root folder:

    python -m unittest test.test_lib

For a specific test:

    python -m unittest test.test_lib.TestLib.test_remove_service

"""

import os
import shutil
import unittest
from pathlib import Path

from pgserviceparser import (
    conf_path,
    full_config,
    remove_service,
    service_config,
    service_names,
    write_service,
    write_service_setting,
)
from pgserviceparser.exceptions import ServiceFileNotFound, ServiceNotFound

PGSERVICEPARSER_SRC_PATH = Path(os.environ["PGSERVICEPARSER_SRC_DIR"])


class TestLib(unittest.TestCase):
    def setUp(self):
        service_file_path_base = PGSERVICEPARSER_SRC_PATH / "test" / "data" / "service_base.txt"
        self.service_file_path = PGSERVICEPARSER_SRC_PATH / "test" / "data" / "pgservice.conf"
        os.environ["PGSERVICEFILE"] = str(self.service_file_path)

        shutil.copy(service_file_path_base, self.service_file_path)

    def test_conf_path(self):
        self.assertEqual(Path(os.environ["PGSERVICEFILE"]), conf_path())

    def test_full_config(self):
        self.assertIsNotNone(full_config())
        self.assertIsNotNone(full_config(self.service_file_path))

        self.assertRaises(ServiceFileNotFound, full_config, "non_existing_file")

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

        self.assertEqual(
            open(self.service_file_path).read().find(" = "),
            -1,
            "Whitespaces between delimiters were found, but should not be present",
        )

        # Overwrite setting
        write_service_setting("service_1", "port", "1")
        conf = service_config("service_1")
        self.assertEqual(conf["port"], "1")

        self.assertEqual(
            open(self.service_file_path).read().find(" = "),
            -1,
            "Whitespaces between delimiters were found, but should not be present",
        )

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

        self.assertEqual(
            open(self.service_file_path).read().find(" = "),
            -1,
            "Whitespaces between delimiters were found, but should not be present",
        )

        # add new service
        new_srv_settings = {"host": "host_4", "dbname": "db_4", "port": 4444, "user": "user_4", "password": "pwd_4"}
        new_srv = write_service(service_name="service_4", settings=new_srv_settings, create_if_not_found=True)
        self.assertIsInstance(new_srv, dict)
        self.assertIn("service_4", service_names())

    def test_create_pgservice_file(self):
        # Create a new service file
        new_service_file_path: Path = PGSERVICEPARSER_SRC_PATH / "test" / "data" / "notexisting" / "pgservice.conf"
        os.environ["PGSERVICEFILE"] = str(new_service_file_path)

        new_srv_settings = {
            "host": "localhost",
            "dbname": "create_me_if_you_can",
            "port": 5566,
            "user": "rw_gis_user",
        }
        new_srv = write_service(service_name="gis_prod_ro", settings=new_srv_settings, create_if_not_found=True)
        self.assertIsInstance(new_srv, dict)
        self.assertIn("gis_prod_ro", service_names())
        self.assertEqual(new_srv["host"], "localhost")
        self.assertEqual(new_srv["dbname"], "create_me_if_you_can")
        self.assertEqual(new_srv["port"], "5566")
        self.assertEqual(new_srv["user"], "rw_gis_user")

        new_service_file_path.unlink()

    def test_remove_service(self):
        with self.assertRaises(ServiceNotFound):
            remove_service("non_existing_service")

        # add new service
        new_srv_settings = {
            "host": "host_5",
            "port": 5555,
        }
        new_srv = write_service(service_name="service_tmp", settings=new_srv_settings, create_if_not_found=True)
        self.assertIsInstance(new_srv, dict)
        self.assertIn("service_tmp", service_names())
        remove_service("service_tmp")

    def test_missing_file(self):
        another_service_file_path = PGSERVICEPARSER_SRC_PATH / "test" / "data" / "new_folder" / "pgservice.conf"
        os.environ["PGSERVICEFILE"] = str(another_service_file_path)

        self.assertEqual(another_service_file_path, conf_path())
        self.assertFalse(another_service_file_path.exists())
        self.assertFalse(another_service_file_path.parent.exists())

        self.assertEqual(another_service_file_path, conf_path(create_if_missing=True))
        self.assertTrue(another_service_file_path.exists())
        self.assertTrue(another_service_file_path.parent.exists())

        os.environ["PGSERVICEFILE"] = str(self.service_file_path)

    def tearDown(self):
        new_folder_path = self.service_file_path.parent / "new_folder"
        if new_folder_path.exists():
            shutil.rmtree(new_folder_path)


if __name__ == "__main__":
    unittest.main()
